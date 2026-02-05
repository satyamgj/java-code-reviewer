import os
import javalang
import chromadb
from chromadb.config import Settings

# Initialize ChromaDB
client = chromadb.PersistentClient(path="./spring_code_db")
collection = client.get_or_create_collection(name="codebase_index")

def get_java_files(root_dir):
    """Recursively find all Java files in the project."""
    for root, _, files in os.walk(root_dir):
        for file in files:
            if file.endswith(".java"):
                yield os.path.join(root, file)

def parse_java_file(file_path):
    """Extract structural data and method-level chunks."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    try:
        tree = javalang.parse.parse(content)
    except:
        return [] # Skip files with syntax errors

    chunks = []
    
    # Analyze classes in the file
    for path, node in tree.filter(javalang.tree.ClassDeclaration):
        class_name = node.name
        # Detect Spring Layer
        layer = "UNKNOWN"
        annotations = [anno.name for anno in node.annotations]
        if "RestController" in annotations: layer = "CONTROLLER"
        elif "Service" in annotations: layer = "SERVICE"
        elif "Repository" in annotations: layer = "REPOSITORY"
        elif "Entity" in annotations: layer = "ENTITY"

        # Break class into Methods
        for method in node.methods:
            method_name = method.name
            
            # Find what this method calls (Simplified)
            calls_to = []
            for _, call in method.filter(javalang.tree.MethodInvocation):
                calls_to.append(f"{call.qualifier or 'this'}.{call.member}")

            # Prepare the searchable text (Class + Method Context)
            doc_text = f"Class: {class_name} ({layer})\nMethod: {method_name}\nCode:\n{content[method.position.line:]}" # Slice for demo

            metadata = {
                "file_path": file_path,
                "class_name": class_name,
                "method_name": method_name,
                "layer": layer,
                "calls_to": ",".join(calls_to[:10]), # Store as CSV string
                "annotations": ",".join(annotations)
            }
            
            chunks.append({
                "id": f"{class_name}_{method_name}",
                "text": doc_text,
                "metadata": metadata
            })
    return chunks

# --- Execution ---
project_path = "/Users/satyamgijare/stable version/13th Feb 23/API/backend-service"
print("Crawling codebase...")

for file in get_java_files(project_path):
    file_chunks = parse_java_file(file)
    for chunk in file_chunks:
        collection.add(
            documents=[chunk["text"]],
            metadatas=[chunk["metadata"]],
            ids=[chunk["id"]]
        )

print("Indexing complete!")