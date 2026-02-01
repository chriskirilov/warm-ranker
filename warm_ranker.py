import weave
import pandas as pd
import os
from langchain.agents import initialize_agent, Tool
from langchain_openai import ChatOpenAI  # Or OpenAI if not chat
from langchain_core.messages import HumanMessage
from langchain.embeddings import HuggingFaceEmbeddings
from redis import Redis
from redis.commands.search.query import Query
from redis.commands.search.field import VectorField
from redis.commands.search.index_definition import IndexDefinition, IndexType
from browserbase import Browserbase
from concurrent.futures import ThreadPoolExecutor
import json
import numpy as np

# Init Weave (leverage MCP in Cursor for auto-tracing queries like "Top runs by score")
try:
    weave.init("warm_ranker_project")
    # LangChain auto-tracing is enabled automatically with weave.init
except Exception as e:
    print(f"Weave initialization skipped: {e}")

# Setups (keys from sponsors/on-site)
redis_client = Redis.from_url(
    "redis://default:e7CZNwiVmLYJeAnKXAbydu49gHum2iq4@redis-15060.c60.us-west-1-2.ec2.cloud.redislabs.com:15060",
    decode_responses=True
)

# Create index if not exists (JSON type, with vector at root $.vector)
try:
    redis_client.ft("contact_idx").info()  # Check if exists
except:
    vector_field = VectorField("$.vector", "FLAT", {
        "TYPE": "FLOAT32", 
        "DIM": 384,  # From all-MiniLM-L6-v2 model
        "DISTANCE_METRIC": "COSINE"
    }, as_name="vector")  # Alias for query
    definition = IndexDefinition(prefix=["contact:"], index_type=IndexType.JSON)
    redis_client.ft("contact_idx").create_index(fields=[vector_field], definition=definition)

embedder = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
try:
    llm = ChatOpenAI(
        model="meta-llama/Llama-3.1-8B-Instruct",  # Choose from supported: e.g., Llama-3.1-8B-Instruct (fast/cheap for hackathon)
        temperature=0.5,
        api_key=os.environ.get("WANDB_API_KEY", "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"),  # Your key from earlier
        base_url="https://api.inference.wandb.ai/v1",
        extra_headers={"OpenAI-Project": "pipelineom/warm_ranker"}  # Your entity/project for tracking/credits
    )
except Exception as e:
    print(f"ChatOpenAI initialization skipped: {e}")
    try:
        # Fallback to regular OpenAI
        from langchain_openai import OpenAI
        llm = OpenAI(temperature=0.5)
    except Exception as e2:
        print(f"OpenAI initialization skipped: {e2}")
        llm = None
bb = Browserbase(api_key='bb_live_4S84BLlgfSsxbWNkXCHA9dnLkK0')

def enrich_profile(url):
    try:
        content = bb.scrape(url)
        # ChatOpenAI uses invoke with messages
        response = llm.invoke([HumanMessage(content=f"Extract concise bio and skills summary from: {content[:2000]}")])
        bio = response.content if hasattr(response, 'content') else str(response)
        return bio
    except:
        return "Enrichment failed"

tools = [Tool(name="EnrichProfile", func=enrich_profile, description="Summarize public LinkedIn profile bio/skills")]

if llm:
    agent = initialize_agent(tools, llm, agent_type="zero-shot-react-description")
else:
    agent = None

def process_contacts(csv_path, idea, max_workers=5):
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
        redis_client.json().set(f"contact:{i}", '.', {"data": contact, "vector": embed_array.tolist(), "profile_text": profile_text})
    
    return contacts

@weave.op()
def warm_ranker(idea, iterations=2, index_name="contact_idx"):
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
    
    for i in range(iterations):
        for candidate in candidates:
            analysis = agent.run(f"{prompt} Analyze profile: {candidate['profile_text']}")
            # Parse score (improve with regex if needed)
            score_str = analysis.split('Score:')[1].strip().split()[0] if 'Score:' in analysis else '0'
            candidate['score'] = int(score_str) if score_str.isdigit() else 0
            candidate['reason'] = analysis  # For demo
        
        avg_score = sum(c['score'] for c in candidates) / len(candidates) if candidates else 0
        if avg_score < 7 or i < iterations - 1:
            reflection_response = llm.invoke([HumanMessage(content=f"Review scores: {str([c['score'] for c in candidates])}. Suggest prompt improvements for '{idea}'.")])
            reflection = reflection_response.content if hasattr(reflection_response, 'content') else str(reflection_response)
            prompt_response = llm.invoke([HumanMessage(content=f"Refine this prompt: {prompt} based on {reflection}")])
            prompt = prompt_response.content if hasattr(prompt_response, 'content') else str(prompt_response)
        
        # Logging handled automatically by @weave.op() decorator
        # weave.log_call({"iteration": i, "avg_score": avg_score, "prompt": prompt, "sample_scores": [c['score'] for c in candidates[:5]]})
    
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

# Redis test
try:
    print("Redis connected:", redis_client.ping())
except Exception as e:
    print("Redis error:", str(e))

# Quick test (create mock CSV)
if __name__ == "__main__":
    mock_data = [
        {'First Name': 'John', 'Last Name': 'Doe', 'Company': 'AI Marketing Inc', 'Position': 'CTO', 'URL': 'https://linkedin.com/in/johndoe'},
        {'First Name': 'Jane', 'Last Name': 'Smith', 'Company': 'Tech Startup', 'Position': 'Marketer', 'URL': 'https://linkedin.com/in/janesmith'}
    ]
    pd.DataFrame(mock_data).to_csv('mock_contacts.csv', index=False)
    result = main("AI tools for marketing automation", "mock_contacts.csv")
    print(f"Ranked {len(result)} contacts")
