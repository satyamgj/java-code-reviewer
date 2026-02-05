import chromadb
from openai import OpenAI
import argparse
import sys

# Initialize
client = chromadb.PersistentClient(path="./spring_code_db")
collection = client.get_collection(name="codebase_index")
llm_client = OpenAI() 

def trace_code_flow(user_query, max_depth=5):
    flow_snippets = []
    
    # STEP 1: Semantic Entry Point Search
    # We broaden the search to 3 results to find the most relevant controller
    initial_results = collection.query(
        query_texts=[user_query],
        n_results=1,
        where={"layer": "CONTROLLER"} 
    )
    
    if not initial_results['ids'][0]:
        return "No entry point found in Controller layer."

    current_id = initial_results['ids'][0][0]

    # STEP 2: Intelligent Trace Walking
    visited_ids = set()
    for _ in range(max_depth):
        if current_id in visited_ids: break
        visited_ids.add(current_id)

        # Get current node details
        res = collection.get(ids=[current_id])
        if not res['ids']: break
        
        node = {
            "id": res['ids'][0],
            "metadata": res['metadatas'][0],
            "document": res['documents'][0]
        }
        flow_snippets.append(node)

        # Identify next hop: Look for Service or Repository calls
        calls = node['metadata'].get('calls_to', "").split(",")
        next_id = None
        
        for call in calls:
            # Skip noise like loggers or common java utils
            if any(x in call.lower() for x in ["log", "this", "stream", "collections"]):
                continue
            
            method_name = call.split(".")[-1]
            # Search for the implementation of this method
            next_step = collection.get(where={"method_name": method_name})
            
            if next_step['ids']:
                # Heuristic: Prioritize SERVICE -> REPOSITORY flow
                next_id = next_step['ids'][0]
                break 
        
        if next_id:
            current_id = next_id
        else:
            break

    return flow_snippets

def main():
    parser = argparse.ArgumentParser(description="Developer-Focused Request Flow Tracer")
    parser.add_argument("query", type=str, help="Technical query")
    parser.add_argument("--depth", type=int, default=5)
    args = parser.parse_args()

    print(f"--- Technical Trace: {args.query} ---")
    flow = trace_code_flow(args.query, max_depth=args.depth)
    
    if isinstance(flow, str):
        print(flow)
        return

    # STEP 3: Developer-Focused Context Construction
    context_blocks = []
    for s in flow:
        block = (
            f"FILE: {s['metadata']['file_path']}\n"
            f"CLASS: {s['metadata']['class_name']} (@{s['metadata']['layer']})\n"
            f"METHOD: {s['metadata']['method_name']}\n"
            f"CODE:\n{s['document']}\n"
            f"{'='*40}"
        )
        context_blocks.append(block)
    
    full_context = "\n\n".join(context_blocks)

    # STEP 4: The "Senior Lead" System Prompt
    system_instruction = (
        "You are a Senior Technical Architect. Your goal is to help a developer "
        "understand exactly how a request propagates through this Spring Boot system.\n\n"
        "REQUIRED OUTPUT FORMAT:\n"
        "1. **Execution Sequence**: A Mermaid-style flow or simple arrow diagram.\n"
        "2. **Logic Deep Dive**: Analyze the 'why'. Mention @Transactional boundaries, "
        "DTO-to-Entity mappings, and specific business logic branch points.\n"
        "3. **Dependency Resolutions**: Clarify Interface -> Implementation jumps.\n"
        "4. **Developer Advisory**: Point out side effects (DB writes, events) and "
        "critical files a dev must modify to change this behavior.\n\n"
        "Maintain a technical, concise, and no-fluff tone."
    )

    response = llm_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": f"Query: {args.query}\n\nCodebase Context:\n{full_context}"}
        ]
    )

    print(response.choices[0].message.content)

if __name__ == "__main__":
    main()