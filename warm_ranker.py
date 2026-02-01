import weave
import pandas as pd
from langchain.agents import initialize_agent, Tool
from langchain.llms import OpenAI
from langchain.embeddings import HuggingFaceEmbeddings
from redis import Redis
from redis.commands.search.query import Query
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
embedder = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
try:
    # Switch to W&B proxy
    llm = OpenAI(
        openai_api_key="wandb_inference_proxy",  # Magic key for proxy
        base_url="https://api.wandb.ai/inference/v1",  # W&B endpoint
        temperature=0.5
    )
except Exception as e:
    print(f"W&B OpenAI proxy initialization skipped: {e}")
    try:
        # Fallback to regular OpenAI
        llm = OpenAI(temperature=0.5)
    except Exception as e2:
        print(f"OpenAI initialization skipped: {e2}")
        llm = None
bb = Browserbase(api_key='bb_live_4S84BLlgfSsxbWNkXCHA9dnLkK0')

def enrich_profile(url):
    try:
        content = bb.scrape(url)
        bio = llm(f"Extract concise bio and skills summary from: {content[:2000]}")
        return bio
    except:
        return "Enrichment failed"

tools = [Tool(name="EnrichProfile", func=enrich_profile, description="Summarize public LinkedIn profile bio/skills")]

if llm:
    agent = initialize_agent(tools, llm, agent_type="zero-shot-react-description")
else:
    agent = None

def setup_redis_index(dimension=384, index_name="contact_idx"):  # all-MiniLM-L6-v2 has 384 dimensions
    """Create Redis search index for vector similarity search"""
    from redis.commands.search.field import VectorField, TextField
    from redis.commands.search.index_definition import IndexDefinition, IndexType
    from redis.exceptions import ResponseError
    
    try:
        # Check if index exists
        redis_client.ft(index_name).info()
        print(f"Redis index '{index_name}' already exists")
    except ResponseError as e:
        if "no such index" in str(e).lower() or "unknown index" in str(e).lower():
            # Create index if it doesn't exist
            schema = (
                VectorField("$.vector", "FLAT", {  # JSON path for vector field
                    "TYPE": "FLOAT32",
                    "DIM": dimension,
                    "DISTANCE_METRIC": "COSINE"
                }),
                TextField("$.profile_text"),  # JSON path for text field
            )
            
            redis_client.ft(index_name).create_index(
                schema,
                definition=IndexDefinition(prefix=["contact:"], index_type=IndexType.JSON)
            )
            print(f"Redis index '{index_name}' created successfully")
        else:
            raise

def process_contacts(csv_path, idea, max_workers=5):
    df = pd.read_csv(csv_path)  # Assumes LinkedIn export columns: First Name, Last Name, Company, Position, URL
    contacts = df.to_dict('records')
    
    # Setup Redis index for vector search
    setup_redis_index()
    
    # Parallel enrichment
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(enrich_profile, contact.get('URL', '')) for contact in contacts]
        for i, future in enumerate(futures):
            contacts[i]['enriched_bio'] = future.result()
    
    # Embed and store in Redis for semantic search
    for i, contact in enumerate(contacts):
        profile_text = f"{contact.get('Position', '')} at {contact.get('Company', '')} - Bio: {contacts[i]['enriched_bio']}"
        embed = embedder.embed_query(profile_text)
        # Convert embed to numpy array for storage (Redis JSON stores as list)
        embed_array = np.array(embed, dtype=np.float32)
        # Store vector as list in JSON (Redis handles conversion for vector search)
        redis_client.json().set(f"contact:{i}", '.', {"data": contact, "vector": embed_array.tolist(), "profile_text": profile_text})
    
    return contacts

@weave.op()
def warm_ranker(idea, iterations=2, index_name="contact_idx"):
    # Semantic pre-filter top candidates
    idea_embed = embedder.embed_query(idea)
    idea_embed_bytes = np.array(idea_embed, dtype=np.float32).tobytes()  # Ensure float32 for Redis
    total = redis_client.dbsize()
    k = min(50, total)  # Adjust based on contacts
    # Updated syntax for binary vector with dialect 2
    query = (Query("*=>[KNN $K @vector $VEC PARAMS 0]")  # Updated syntax for binary vector
             .return_fields("data", "profile_text")
             .paging(0, k)  # Paginate if needed
             .dialect(2))
    results = redis_client.ft(index_name).search(query, query_params={"K": k, "VEC": idea_embed_bytes})  # Use index name
    
    candidates = [json.loads(res['data']) for res in results.docs if 'data' in res]
    
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
            reflection = llm(f"Review scores: {str([c['score'] for c in candidates])}. Suggest prompt improvements for '{idea}'.")
            prompt = llm(f"Refine this prompt: {prompt} based on {reflection}")
        
        weave.log({"iteration": i, "avg_score": avg_score, "prompt": prompt, "sample_scores": [c['score'] for c in candidates[:5]]})
    
    # Final sort
    candidates.sort(key=lambda x: x['score'], reverse=True)
    return candidates

def main(idea, csv_path):
    process_contacts(csv_path, idea)
    ranked = warm_ranker(idea)
    df_ranked = pd.DataFrame([{**c['data'], 'score': c['score'], 'reason': c['reason']} for c in ranked])
    print(df_ranked.to_markdown())  # For console; export to UI later
    weave.log({"final_ranked": df_ranked.to_dict()})  # Viz in Weave dashboard

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
    main("AI tools for marketing automation", "mock_contacts.csv")
