import os
import sys
import javalang
import chromadb
import hashlib
import re

# --- Argument Handling ---
# Usage: python crawler.py "/path/to/project" [--reset]
if len(sys.argv) < 2:
    print("Usage: python crawler.py <project_path> [--reset]")
    sys.exit(1)

project_path = sys.argv[1]
reset_db = "--reset" in sys.argv

# --- Initialize ChromaDB ---
client = chromadb.PersistentClient(path="./spring_code_db")

# If reset flag is provided, delete the old collection to start fresh
if reset_db:
    try:
        client.delete_collection(name="codebase_index")
        print("Existing index cleared.")
    except:
        pass 

collection = client.get_or_create_collection(name="codebase_index")

# ... (Keep your get_java_files and parse_java_file functions exactly as they were) ...

def get_java_files(root_dir):
    for root, _, files in os.walk(root_dir):
        for file in files:
            if file.endswith(".java"):
                yield os.path.join(root, file)

# def parse_java_file(file_path):
#     with open(file_path, 'r', encoding='utf-8') as f:
#         content = f.read()
#     try:
#         tree = javalang.parse.parse(content)
#     except:
#         return []

#     chunks = []
#     for path, node in tree.filter(javalang.tree.ClassDeclaration):
#         class_name = node.name
#         layer = "UNKNOWN"
#         annotations = [anno.name for anno in node.annotations]
#         if "RestController" in annotations: layer = "CONTROLLER"
#         elif "Service" in annotations: layer = "SERVICE"
#         elif "Repository" in annotations: layer = "REPOSITORY"
#         elif "Entity" in annotations: layer = "ENTITY"

#         for method in node.methods:
#             method_name = method.name
#             calls_to = []
#             for _, call in method.filter(javalang.tree.MethodInvocation):
#                 calls_to.append(f"{call.qualifier or 'this'}.{call.member}")

#             doc_text = f"Class: {class_name} ({layer})\nMethod: {method_name}\nCode:\n{content[method.position.line:]}"

#             metadata = {
#                 "file_path": file_path,
#                 "class_name": class_name,
#                 "method_name": method_name,
#                 "layer": layer,
#                 "calls_to": ",".join(calls_to[:10]),
#                 "annotations": ",".join(annotations)
#             }
            
#             chunks.append({
#                 "id": f"{class_name}_{method_name}",
#                 "text": doc_text,
#                 "metadata": metadata
#             })
#     return chunks

# def parse_java_file(file_path):
#     with open(file_path, 'r', encoding='utf-8') as f:
#         content = f.read()
#     try:
#         tree = javalang.parse.parse(content)
#     except:
#         return []

#     chunks = []
#     for path, node in tree.filter(javalang.tree.ClassDeclaration):
#         class_name = node.name
#         layer = "UNKNOWN"
#         annotations = [anno.name for anno in node.annotations]
        
#         if "RestController" in annotations: layer = "CONTROLLER"
#         elif "Service" in annotations: layer = "SERVICE"
#         elif "Repository" in annotations: layer = "REPOSITORY"
#         elif "Entity" in annotations: layer = "ENTITY"

#         for method in node.methods:
#             method_name = method.name
#             line_no = method.position.line
#             calls_to = []
#             for _, call in method.filter(javalang.tree.MethodInvocation):
#                 calls_to.append(f"{call.qualifier or 'this'}.{call.member}")

#             doc_text = f"Class: {class_name} ({layer})\nMethod: {method_name}\nCode:\n{content[line_no:]}"

#             # Create a unique hash of the file path and line number to prevent duplicates
#             unique_suffix = hashlib.md5(f"{file_path}_{line_no}".encode()).hexdigest()[:8]
            
#             metadata = {
#                 "file_path": file_path,
#                 "class_name": class_name,
#                 "method_name": method_name,
#                 "layer": layer,
#                 "calls_to": ",".join(calls_to[:10]),
#                 "annotations": ",".join(annotations)
#             }
            
#             chunks.append({
#                 # New ID format: ClassName_MethodName_ShortHash
#                 "id": f"{class_name}_{method_name}_{unique_suffix}",
#                 "text": doc_text,
#                 "metadata": metadata
#             })
#     return chunks



def generate_summary(class_name, method_name, annotations, calls_to):
    """
    Simulates a logic summary. In a real setup, pass this to a small LLM.
    This provides the 'Natural Language' bridge for the vector search.
    """
    layer_intent = "API Entry point" if "CONTROLLER" in annotations else "Business Logic"
    return f"This {layer_intent} in {class_name} handles {method_name}. It interacts with {', '.join(calls_to) if calls_to else 'local data'}."

# def parse_java_file(file_path):
#     with open(file_path, 'r', encoding='utf-8') as f:
#         content = f.read()
#     try:
#         tree = javalang.parse.parse(content)
#     except: return []

#     chunks = []
#     # Identify Interfaces implemented by the class
#     for path, node in tree.filter(javalang.tree.ClassDeclaration):
#         class_name = node.name
#         implements = [i.name for i in node.implements] if node.implements else []
        
#         # Layer Detection
#         annotations = [anno.name for anno in node.annotations]
#         layer = "CONTROLLER" if "RestController" in annotations else \
#                 "SERVICE" if "Service" in annotations else \
#                 "REPOSITORY" if "Repository" in annotations else "COMPONENT"

#         for method in node.methods:
#             method_name = method.name
#             line_no = method.position.line
            
#             # Extract Calls (The Plumbing)
#             calls_to = []
#             for _, call in method.filter(javalang.tree.MethodInvocation):
#                 calls_to.append(f"{call.qualifier or 'this'}.{call.member}")

#             # 1. BUILD THE SEMANTIC SUMMARY (For better Vector Hits)
#             summary = generate_summary(class_name, method_name, layer, calls_to[:3])
            
#             # 2. ENRICHED DOCUMENT (The Context)
#             # We include the summary INSIDE the document so the vector search hits the summary
#             doc_text = (
#                 f"SUMMARY: {summary}\n"
#                 f"CONTEXT: Class {class_name} implements {implements}\n"
#                 f"METHOD: {method_name}\n"
#                 f"CODE:\n{content[line_no:]}"
#             )

#             unique_suffix = hashlib.md5(f"{file_path}_{line_no}".encode()).hexdigest()[:8]
            
#             metadata = {
#                 "file_path": file_path,
#                 "class_name": class_name,
#                 "method_name": method_name,
#                 "layer": layer,
#                 "implements": ",".join(implements),
#                 "calls_to": ",".join(calls_to[:15]), # Relationship mapping
#                 "return_type": str(method.return_type.name if method.return_type else "void")
#             }
            
#             chunks.append({
#                 "id": f"{class_name}_{method_name}_{unique_suffix}",
#                 "text": doc_text,
#                 "metadata": metadata
#             })
#     return chunks

def extract_endpoint_path(node):
    """
    Extracts the 'value' or 'path' string from Spring Mapping annotations.
    """
    if not hasattr(node, 'annotations'):
        return None
        
    for anno in node.annotations:
        if any(x in anno.name for x in ["Mapping", "GetMapping", "PostMapping", "PutMapping", "DeleteMapping"]):
            # Case 1: @GetMapping("/path") -> element is a Literal or list of literals
            if anno.element:
                if isinstance(anno.element, javalang.tree.Literal):
                    return anno.element.value.strip('"')
                # Case 2: @GetMapping(path="/path") or @GetMapping(value="/path")
                if isinstance(anno.element, list):
                    for pair in anno.element:
                        if hasattr(pair, 'name') and pair.name in ["value", "path"]:
                            if hasattr(pair.value, 'value'):
                                return pair.value.value.strip('"')
    return None

def parse_java_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        full_content = f.read()
    try:
        tree = javalang.parse.parse(full_content)
    except:
        return []

    chunks = []
    
    for _, node in tree.filter(javalang.tree.ClassDeclaration):
        class_name = node.name
        implements = [i.name for i in node.implements] if node.implements else []
        
        # 1. Base API Path (Class-level @RequestMapping)
        base_path = extract_endpoint_path(node) or ""
        
        # 2. Layer Detection
        class_annotations = [anno.name for anno in node.annotations]
        layer = "CONTROLLER" if "RestController" in class_annotations or "Controller" in class_annotations else \
                "SERVICE" if "Service" in class_annotations else \
                "REPOSITORY" if "Repository" in class_annotations else "COMPONENT"

        for method in node.methods:
            method_name = method.name
            line_no = method.position.line
            method_annotations = [anno.name for anno in method.annotations]
            
            # 3. Full Endpoint Resolution
            method_path = extract_endpoint_path(method)
            full_endpoint = f"{base_path}{method_path}" if method_path else None
            
            # 4. Extract Method Calls (Plumbing)
            calls_to = []
            for _, call in method.filter(javalang.tree.MethodInvocation):
                calls_to.append(f"{call.qualifier or 'this'}.{call.member}")

            # 5. Logic Pattern Detection (The 'Why')
            # Look for Event Publishers or common modification keywords
            method_body_sample = full_content[line_no:line_no+2000] # Sample for pattern matching
            is_publisher = "publishEvent" in method_body_sample
            is_listener = "EventListener" in method_annotations
            is_modifier = any(x in method_name.lower() for x in ["update", "save", "delete", "patch", "change"])

            # 6. Content Sanitization (Remove excessive noise/backslashes)
            # We take the method block and clean it for the LLM
            raw_code = full_content.splitlines()[line_no-1 : line_no+50] # Take ~50 lines
            clean_code = "\n".join(raw_code).replace('\\n', '\n').replace('\\"', '"')

            # 7. Metadata Enrichment
            metadata = {
                "file_path": file_path,
                "class_name": class_name,
                "method_name": method_name,
                "layer": layer,
                "endpoint": full_endpoint if full_endpoint else "N/A",
                "implements": ",".join(implements),
                "calls_to": ",".join(calls_to[:15]),
                "is_publisher": str(is_publisher),
                "is_listener": str(is_listener),
                "is_modifier": str(is_modifier),
                "return_type": str(method.return_type.name if method.return_type else "void")
            }

            # Unique ID based on location to prevent collisions
            unique_suffix = hashlib.md5(f"{file_path}_{line_no}".encode()).hexdigest()[:8]
            
            chunks.append({
                "id": f"{class_name}_{method_name}_{unique_suffix}",
                "text": f"CLASS: {class_name}\nMETHOD: {method_name}\nENDPOINT: {full_endpoint}\nCODE:\n{clean_code}",
                "metadata": metadata
            })
            
    return chunks

# --- Execution ---
print(f"Crawling codebase at: {project_path}")

for file in get_java_files(project_path):
    file_chunks = parse_java_file(file)
    if file_chunks:
        # We use upsert so that if the ID exists, it updates; otherwise, it adds.
        collection.upsert(
            documents=[chunk["text"] for chunk in file_chunks],
            metadatas=[chunk["metadata"] for chunk in file_chunks],
            ids=[chunk["id"] for chunk in file_chunks]
        )

print("Indexing complete!")