import chromadb
from openai import OpenAI
import argparse

# Initialize
client = chromadb.PersistentClient(path="./spring_code_db")
collection = client.get_collection(name="codebase_index")
llm_client = OpenAI() # Replace with your preferred LLM

def trace_code_flow(user_query, max_depth=3):
    flow_snippets = []
    
    # STEP 1: Find the entry point using Vector Search
    print(f"Finding entry point for: {user_query}")
    initial_results = collection.query(
        query_texts=[user_query],
        n_results=1,
        where={"layer": "CONTROLLER"} # Force it to look for entry points first
    )
    
    if not initial_results['ids'][0]:
        return "No entry point found."

    current_chunk = {
        "id": initial_results['ids'][0][0],
        "metadata": initial_results['metadatas'][0][0],
        "document": initial_results['documents'][0][0]
    }
    flow_snippets.append(current_chunk)

    # STEP 2: Recursive Walking
    for _ in range(max_depth):
        calls = current_chunk['metadata'].get('calls_to', "").split(",")
        if not calls or calls == ['']:
            break
            
        # We try to find the first call that matches our internal classes
        # For simplicity, we take the first call in the list
        next_call = calls[0].split(".")[-1] # e.g., "register" from "userService.register"
        
        # Deterministic Metadata Lookup
        next_step = collection.get(
            where={"method_name": next_call}
        )
        
        if next_step['ids']:
            current_chunk = {
                "id": next_step['ids'][0],
                "metadata": next_step['metadatas'][0],
                "document": next_step['documents'][0]
            }
            flow_snippets.append(current_chunk)
        else:
            break # Path ended or call is external (like a library)

    return flow_snippets

# --- Example Execution ---
# uery = "how is the relationship between BOM and User?"
# flow = trace_code_flow(query)q


def main():
    # 1. Setup the Argument Parser
    parser = argparse.ArgumentParser(
        description="Spring Boot Request Flow Tracer",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    # 2. Add the 'query' parameter
    parser.add_argument(
        "query", 
        type=str, 
        help="The natural language question about your code (e.g., 'How are users registered?')"
    )
    
    # 3. Optional: Add a 'depth' parameter
    parser.add_argument(
        "--depth", 
        type=int, 
        default=3, 
        help="How many method hops to follow in the trace"
    )

    args = parser.parse_args()

    # 4. Execute the trace using the command line input
    print(f"--- Tracing Flow for: '{args.query}' (Depth: {args.depth}) ---")
    
    flow = trace_code_flow(args.query, max_depth=args.depth)
    
    # Process and print results
    if isinstance(flow, str):
        print(flow)
    else:
        for i, step in enumerate(flow):
            print(f"Step {i+1}: {step['metadata']['class_name']}.{step['metadata']['method_name']}")
            print(f"Path: {step['metadata']['file_path']}\n")
    
        # Prepare context for LLM
    context = "\n\n".join([f"File: {s['metadata']['file_path']}\n{s['document']}" for s in flow])

    response = llm_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a Spring Boot expert. Explain the request flow based on these snippets."},
            {"role": "user", "content": f"Query: {args.query}\n\nCode Context:\n{context}"}
        ]
    )

    print("\n--- Explanation ---")

    print(response.choices[0].message.content)


if __name__ == "__main__":
    main()