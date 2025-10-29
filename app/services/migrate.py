"""
Migrate existing Chroma vector database to Qdrant
This preserves your working embeddings without re-indexing
"""

from dotenv import load_dotenv
import os
from langchain_community.vectorstores import Chroma
from langchain_qdrant import QdrantVectorStore
from langchain_openai import OpenAIEmbeddings
from qdrant_client import QdrantClient, models
from langchain.schema import Document

# Load environment variables
load_dotenv()

# Configuration
CHROMA_PERSIST_DIR = "./fossils-db"
CHROMA_COLLECTION_NAME = "fossils_collection"
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "fossils_classification")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def main():
    print("="*80)
    print("🔄 MIGRATING CHROMA → QDRANT")
    print("="*80)
    
    # Step 1: Initialize embeddings (same model as original)
    print("\n🔮 Step 1: Initializing embeddings...")
    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-large",
        openai_api_key=OPENAI_API_KEY
    )
    print("✅ Embeddings initialized")
    
    # Step 2: Load from Chroma
    print("\n📦 Step 2: Loading existing Chroma database...")
    print(f"   Location: {CHROMA_PERSIST_DIR}")
    print(f"   Collection: {CHROMA_COLLECTION_NAME}")
    
    try:
        chroma_db = Chroma(
            persist_directory=CHROMA_PERSIST_DIR,
            embedding_function=embeddings,
            collection_name=CHROMA_COLLECTION_NAME
        )
        print("✅ Chroma database loaded")
    except Exception as e:
        print(f"❌ ERROR loading Chroma: {e}")
        return
    
    # Step 3: Extract all documents
    print("\n📄 Step 3: Extracting documents from Chroma...")
    try:
        # Get all data from Chroma
        all_data = chroma_db.get()
        
        # Reconstruct Document objects
        documents = []
        for i in range(len(all_data['ids'])):
            doc = Document(
                page_content=all_data['documents'][i],
                metadata=all_data['metadatas'][i] if all_data['metadatas'] else {}
            )
            documents.append(doc)
        
        print(f"✅ Extracted {len(documents)} documents")
        
        # Show sample
        print(f"\n📝 Sample document (first 300 chars):")
        print("-"*80)
        print(documents[0].page_content[:300])
        print("-"*80)
        
    except Exception as e:
        print(f"❌ ERROR extracting documents: {e}")
        return
    
    # Step 4: Connect to Qdrant
    print("\n🔌 Step 4: Connecting to Qdrant...")
    print(f"   URL: {QDRANT_URL}")
    print(f"   Collection: {QDRANT_COLLECTION}")
    
    try:
        qdrant_client = QdrantClient(
            url=QDRANT_URL,
            api_key=QDRANT_API_KEY,
            prefer_grpc=False
        )
        print("✅ Connected to Qdrant")
    except Exception as e:
        print(f"❌ ERROR connecting to Qdrant: {e}")
        return
    
    # Step 5: Check if collection exists
    print("\n🔍 Step 5: Checking Qdrant collection status...")
    try:
        collections = qdrant_client.get_collections().collections
        collection_names = [c.name for c in collections]
        
        if QDRANT_COLLECTION in collection_names:
            print(f"⚠️  Collection '{QDRANT_COLLECTION}' already exists")
            confirm = input("   Delete and recreate? (yes/no): ").strip().lower()
            
            if confirm == 'yes':
                print(f"🗑️  Deleting existing collection...")
                qdrant_client.delete_collection(QDRANT_COLLECTION)
                print("✅ Collection deleted")
            else:
                print("❌ Migration cancelled")
                return
        else:
            print(f"✅ Collection '{QDRANT_COLLECTION}' does not exist (will create)")
            
    except Exception as e:
        print(f"❌ ERROR checking collection: {e}")
        return
    
    # Step 6: Upload to Qdrant
    print("\n📤 Step 6: Uploading documents to Qdrant...")
    print(f"   Total documents: {len(documents)}")
    print("   ⏳ This may take a few minutes...")
    
    try:
        vectorstore = QdrantVectorStore.from_documents(
            documents=documents,
            embedding=embeddings,
            url=QDRANT_URL,
            api_key=QDRANT_API_KEY,
            collection_name=QDRANT_COLLECTION,
            prefer_grpc=False,
            force_recreate=True
        )
        print(f"✅ Successfully uploaded {len(documents)} documents to Qdrant!")
    except Exception as e:
        print(f"❌ ERROR uploading to Qdrant: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Step 7: Verify migration
    print("\n🧪 Step 7: Verifying migration...")
    try:
        collection_info = qdrant_client.get_collection(QDRANT_COLLECTION)
        print(f"✅ Collection info:")
        print(f"   - Vectors: {collection_info.points_count}")
        print(f"   - Vector size: {collection_info.config.params.vectors.size}")
        
        # Test retrieval
        print("\n🔍 Testing retrieval with sample query...")
        results = vectorstore.similarity_search(
            "What are the classification rules for fossil teeth?",
            k=3
        )
        
        print(f"✅ Found {len(results)} results")
        print(f"\n📄 Top result preview (first 200 chars):")
        print("-"*80)
        print(results[0].page_content[:200])
        print("-"*80)
        
    except Exception as e:
        print(f"⚠️  Warning during verification: {e}")
    
    # Step 8: Summary
    print("\n" + "="*80)
    print("🎉 MIGRATION COMPLETE!")
    print("="*80)
    print(f"\n✅ Successfully migrated from Chroma to Qdrant")
    print(f"   - Source: {CHROMA_PERSIST_DIR}")
    print(f"   - Destination: {QDRANT_URL}")
    print(f"   - Collection: {QDRANT_COLLECTION}")
    print(f"   - Documents: {len(documents)}")
    print(f"\n💡 Next steps:")
    print(f"   1. Update app/services/rag.py to use Qdrant")
    print(f"   2. Test with: python test_qdrant_retrieval.py")
    print(f"   3. Run your RAG: python -m app.services.rag")
    print("="*80)

if __name__ == "__main__":
    main()