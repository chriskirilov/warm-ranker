import weave
import pandas as pd
import os
import sys
import json
import numpy as np
from langchain.agents import initialize_agent, Tool
from langchain_openai import ChatOpenAI  # Or OpenAI if not chat
from langchain_core.messages import HumanMessage
from langchain_community.embeddings import HuggingFaceEmbeddings
from redis import Redis
from redis.commands.search.query import Query
from redis.commands.search.field import VectorField
from redis.commands.search.index_definition import IndexDefinition, IndexType
from browserbase import Browserbase
from concurrent.futures import ThreadPoolExecutor

# Lazy-loaded globals for serverless compatibility
_redis_client = None
_embedder = None
_llm = None
_agent = None
_bb = None
_weave_initialized = False

def get_redis_client():
    """Lazy-load Redis client to avoid cold start issues"""
    global _redis_client
    if _redis_client is None:
        _redis_client = Redis.from_url(
            "redis://default:e7CZNwiVmLYJeAnKXAbydu49gHum2iq4@redis-15060.c60.us-west-1-2.ec2.cloud.redislabs.com:15060",
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5
        )
        # Create index if not exists
        try:
            _redis_client.ft("contact_idx").info()
        except:
            try:
                vector_field = VectorField("$.vector", "FLAT", {
                    "TYPE": "FLOAT32", 
                    "DIM": 384,
                    "DISTANCE_METRIC": "COSINE"
                }, as_name="vector")
                definition = IndexDefinition(prefix=["contact:"], index_type=IndexType.JSON)
                _redis_client.ft("contact_idx").create_index(fields=[vector_field], definition=definition)
            except Exception as e:
                print(f"Redis index creation error: {e}", file=sys.stderr)
    return _redis_client

def get_embedder():
    """Lazy-load embedder to avoid cold start delays"""
    global _embedder
    if _embedder is None:
        _embedder = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    return _embedder

def get_llm():
    """Lazy-load LLM to avoid cold start delays"""
    global _llm
    if _llm is None:
        try:
            _llm = ChatOpenAI(
                model="meta-llama/Llama-3.1-8B-Instruct",
                temperature=0.5,
                api_key=os.environ.get("WANDB_API_KEY", "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"),
                base_url="https://api.inference.wandb.ai/v1",
                extra_headers={"OpenAI-Project": "pipelineom/warm_ranker"}
            )
        except Exception as e:
            print(f"ChatOpenAI initialization skipped: {e}", file=sys.stderr)
            try:
                from langchain_openai import OpenAI
                _llm = OpenAI(temperature=0.5)
            except Exception as e2:
                print(f"OpenAI initialization skipped: {e2}", file=sys.stderr)
                _llm = None
    return _llm

def get_browserbase():
    """Lazy-load Browserbase client"""
    global _bb
    if _bb is None:
        _bb = Browserbase(api_key='bb_live_4S84BLlgfSsxbWNkXCHA9dnLkK0')
    return _bb

def get_agent():
    """Lazy-load agent"""
    global _agent
    if _agent is None:
        llm = get_llm()
        if llm:
            def enrich_profile(url):
                try:
                    bb = get_browserbase()
                    content = bb.scrape(url)
                    llm_instance = get_llm()
                    if llm_instance:
                        response = llm_instance.invoke([HumanMessage(content=f"Extract concise bio and skills summary from: {content[:2000]}")])
                        bio = response.content if hasattr(response, 'content') else str(response)
                        return bio
                except Exception as e:
                    print(f"Enrichment error: {e}", file=sys.stderr)
                    return "Enrichment failed"
            
            tools = [Tool(name="EnrichProfile", func=enrich_profile, description="Summarize public LinkedIn profile bio/skills")]
            _agent = initialize_agent(tools, llm, agent_type="zero-shot-react-description")
    return _agent

def init_weave():
    """Lazy-init Weave"""
    global _weave_initialized
    if not _weave_initialized:
        try:
            weave.init("warm_ranker_project")
            _weave_initialized = True
        except Exception as e:
            print(f"Weave initialization skipped: {e}", file=sys.stderr)

def enrich_profile(url):
    """Enrich a single profile"""
    try:
        bb = get_browserbase()
        content = bb.scrape(url)
        llm = get_llm()
        if llm:
            response = llm.invoke([HumanMessage(content=f"Extract concise bio and skills summary from: {content[:2000]}")])
            bio = response.content if hasattr(response, 'content') else str(response)
            return bio
        return "LLM not available"
    except Exception as e:
        print(f"Enrichment error: {e}", file=sys.stderr)
        return "Enrichment failed"

def process_contacts(csv_path, idea, max_workers=5):
    init_weave()  # Initialize Weave on first use
    redis_client = get_redis_client()
    embedder = get_embedder()
    
    df = pd.read_csv(csv_path)  # Assumes LinkedIn export columns: First Name, Last Name, Company, Position, URL
    contacts = df.to_dict('records')
    
    # Parallel enrichment
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(enrich_profile, contact.get('URL', '')) for contact in contacts]
        for i, future in enumerate(futures):
            contacts[i]['enriched_bio'] = future.result()
    
    # Embed and store in Redis for semantic search
    for i, contact in enumerate(contacts):
        profile_text = f"{contact.get('Position', '')} at {contact.get('Company', '')} - Bio: {contacts[i]['enriched_bio']}"
        embed = embedder.embed_query(profile_text)
        # Store as list in JSON (Redis converts to bytes internally for vector search)
        embed_array = np.array(embed, dtype=np.float32)
        try:
            redis_client.json().set(f"contact:{i}", '.', {"data": contact, "vector": embed_array.tolist(), "profile_text": profile_text})
        except Exception as e:
            print(f"Redis storage error for contact {i}: {e}", file=sys.stderr)
    
    return contacts

@weave.op()
def warm_ranker(idea, iterations=2, index_name="contact_idx"):
    redis_client = get_redis_client()
    embedder = get_embedder()
    llm = get_llm()
    agent = get_agent()
    
    # Semantic pre-filter top candidates
    idea_embed = embedder.embed_query(idea)
    idea_embed_bytes = np.array(idea_embed, dtype=np.float32).tobytes()
    k = min(50, redis_client.dbsize())  # Adjust K dynamically
    query = (Query("*=>[KNN $K @vector $VEC AS dist]")
             .return_fields("data", "profile_text")
             .sort_by("dist", asc=True)  # Optional: sort by distance
             .dialect(2))
    results = redis_client.ft("contact_idx").search(query, query_params={"K": str(k), "VEC": idea_embed_bytes})
    
    candidates = []
    for doc in results.docs:
        # Access fields from document - Redis returns fields as dict-like or attributes
        data_str = doc.get('data') if hasattr(doc, 'get') else getattr(doc, 'data', None)
        profile_text = doc.get('profile_text') if hasattr(doc, 'get') else getattr(doc, 'profile_text', '')
        
        candidate = {
            'data': json.loads(data_str) if data_str and isinstance(data_str, str) else (data_str if data_str else {}),
            'profile_text': profile_text
        }
        candidates.append(candidate)
    
    prompt = f"Score lead relevance to idea '{idea}' on 1-10 based on title, company, bio. Provide score and brief reason."
    
    if not agent or not llm:
        # Fallback: assign default scores if agent/LLM unavailable
        for candidate in candidates:
            candidate['score'] = 5
            candidate['reason'] = "Agent/LLM not available"
        candidates.sort(key=lambda x: x['score'], reverse=True)
        return candidates
    
    for i in range(iterations):
        for candidate in candidates:
            try:
                analysis = agent.run(f"{prompt} Analyze profile: {candidate['profile_text']}")
                # Parse score (improve with regex if needed)
                score_str = analysis.split('Score:')[1].strip().split()[0] if 'Score:' in analysis else '0'
                candidate['score'] = int(score_str) if score_str.isdigit() else 0
                candidate['reason'] = analysis  # For demo
            except Exception as e:
                print(f"Agent error for candidate: {e}", file=sys.stderr)
                candidate['score'] = 0
                candidate['reason'] = f"Error: {str(e)}"
        
        avg_score = sum(c['score'] for c in candidates) / len(candidates) if candidates else 0
        if avg_score < 7 or i < iterations - 1:
            try:
                reflection_response = llm.invoke([HumanMessage(content=f"Review scores: {str([c['score'] for c in candidates])}. Suggest prompt improvements for '{idea}'.")])
                reflection = reflection_response.content if hasattr(reflection_response, 'content') else str(reflection_response)
                prompt_response = llm.invoke([HumanMessage(content=f"Refine this prompt: {prompt} based on {reflection}")])
                prompt = prompt_response.content if hasattr(prompt_response, 'content') else str(prompt_response)
            except Exception as e:
                print(f"Prompt refinement error: {e}", file=sys.stderr)
                break  # Skip further iterations if refinement fails
    
    # Final sort
    candidates.sort(key=lambda x: x['score'], reverse=True)
    return candidates

def main(idea, csv_path):
    process_contacts(csv_path, idea)
    ranked = warm_ranker(idea)
    df_ranked = pd.DataFrame([{**c['data'], 'score': c['score'], 'reason': c['reason']} for c in ranked])
    # Logging handled automatically by @weave.op() decorator
    # weave.log_call("final_ranked", {"data": df_ranked.to_dict()}, df_ranked.to_dict())
    return df_ranked.to_dict('records')  # Return for JSON response

# Redis test (only in test mode, not when called from API)
if __name__ == "__main__" and len(sys.argv) < 3:
    try:
        redis_client = get_redis_client()
        print("Redis connected:", redis_client.ping(), file=sys.stderr)
    except Exception as e:
        print("Redis error:", str(e), file=sys.stderr)

# Quick test (create mock CSV)
if __name__ == "__main__":
    if len(sys.argv) >= 3:
        # Called from API with command line arguments
        idea = sys.argv[1]
        csv_path = sys.argv[2]
        result = main(idea, csv_path)
        print(json.dumps(result))  # Output JSON for API
    else:
        # Test mode with mock data
        mock_data = [
            {'First Name': 'John', 'Last Name': 'Doe', 'Company': 'AI Marketing Inc', 'Position': 'CTO', 'URL': 'https://linkedin.com/in/johndoe'},
            {'First Name': 'Jane', 'Last Name': 'Smith', 'Company': 'Tech Startup', 'Position': 'Marketer', 'URL': 'https://linkedin.com/in/janesmith'}
        ]
        pd.DataFrame(mock_data).to_csv('mock_contacts.csv', index=False)
        result = main("AI tools for marketing automation", "mock_contacts.csv")
        print(json.dumps(result))  # Output JSON for API