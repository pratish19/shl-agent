import json
import chromadb
import os

# Initialize a local database folder
chroma_client = chromadb.PersistentClient(path="./data/chroma_db")
collection = chroma_client.get_or_create_collection(name="shl_catalog_v2")

def build_vector_db():
    print("Loading pre-scraped catalog.json...")
    if not os.path.exists("data/catalog.json"):
        print("Error: data/catalog.json not found!")
        return

    with open("data/catalog.json", "r", encoding="utf-8") as f:
        catalog = json.load(f)

    if collection.count() > 0:
        print(f"✅ Vector Database already loaded with {collection.count()} tests.")
        return

    documents = []
    metadatas = []
    ids = []

    for i, item in enumerate(catalog):
        name = item.get("name", "Unknown Test")
        url = item.get("link", "") # Mapping 'link' to the required 'url'
        desc = item.get("description", "")
        keys = item.get("keys", [])
        levels = item.get("job_levels", [])
        
        # 1. Determine the 1-letter test_type based on the "keys" array
        # This ensures we meet the strict API schema requirements
        keys_str = " ".join(keys).lower()
        if "personality" in keys_str or "behavior" in keys_str:
            t_type = "P"
        elif "situational" in keys_str or "simulation" in keys_str:
            t_type = "S"
        elif "ability" in keys_str or "aptitude" in keys_str:
            t_type = "A"
        else:
            t_type = "K" # Default to Knowledge

        # 2. Build a super-rich document for the AI to search through
        search_text = f"Test Name: {name}. Type: {t_type}. Description: {desc}. Target Levels: {', '.join(levels)}."
        documents.append(search_text)
        
        # 3. Store ONLY the strictly required fields in the metadata
        metadatas.append({
            "name": name,
            "url": url,
            "test_type": t_type
        })
        ids.append(f"test_{i}")

    print(f"🧠 Embedding {len(catalog)} rich tests into ChromaDB... This might take a minute.")
    
    # Add to Chroma in batches to prevent memory limits
    batch_size = 100
    for j in range(0, len(documents), batch_size):
        collection.add(
            documents=documents[j:j+batch_size],
            metadatas=metadatas[j:j+batch_size],
            ids=ids[j:j+batch_size]
        )
    print("✨ Vector Database built successfully with rich descriptions!")

def search_catalog(query: str, n_results: int = 5):
    results = collection.query(
        query_texts=[query],
        n_results=n_results
    )
    return results["metadatas"][0] if results["metadatas"] else []

if __name__ == "__main__":
    build_vector_db()
    
    print("\n--- Testing Rich Search for: 'Java developer with stakeholders' ---")
    results = search_catalog("Java developer with stakeholders", n_results=3)
    for res in results:
        print(f"- {res['name']} ({res['test_type']})")