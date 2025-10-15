from dotenv import load_dotenv
import os
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import Chroma
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain.callbacks import get_openai_callback
import textwrap

# Load environment variables
load_dotenv("C:\\Users\\ahmed\\Documents\\Flutter\\Paleon\\backend\\.env")

# Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PERSIST_DIR = "./fossils-db"
COLLECTION_NAME = "fossils_collection"

# Helper function
def word_wrap(text, width=100):
    """Wrap text to a given width."""
    return '\n'.join(textwrap.wrap(text, width=width))

# Initialize embeddings (MUST match the indexing embeddings!)
print("🔧 Loading embeddings...")
embeddings = OpenAIEmbeddings(
    model="text-embedding-3-large",
    openai_api_key=OPENAI_API_KEY
)

# Load existing ChromaDB vector store
print("💾 Loading ChromaDB vector store...")
vectorstore = Chroma(
    persist_directory=PERSIST_DIR,
    embedding_function=embeddings,
    collection_name=COLLECTION_NAME
)

# Verify the store has content
doc_count = vectorstore._collection.count()
print(f"✅ Loaded vector store with {doc_count} chunks\n")

if doc_count == 0:
    print("❌ ERROR: No documents in the database. Run indexing first!")
    exit(1)

# Initialize LLM
print("🤖 Initializing ChatGPT...")
llm = ChatOpenAI(
    model="gpt-4o",  # or "gpt-4o" for better quality
    temperature=0,  # 0 = deterministic, 0.7 = creative
    openai_api_key=OPENAI_API_KEY
)

# Create custom prompt template for image classification domain
prompt_template = """You are an expert assistant specializing in image classification and fossil identification procedures.

Use the following context from the technical documentation to answer the question accurately and comprehensively.

Context:
{context}

Question: {question}

Instructions:
- Provide detailed, step-by-step answers when describing procedures
- If the context doesn't contain the answer, say "I don't have enough information in the provided documentation to answer this question."
- When listing procedures, use clear numbered steps
- Cite specific details from the context when relevant
- Be precise and technical when necessary

Answer:"""

PROMPT = PromptTemplate(
    template=prompt_template,
    input_variables=["context", "question"]
)

# Create retrieval QA chain
print("⚙️ Building QA chain...\n")
qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    chain_type="stuff",  # "stuff" = put all context in one prompt
    retriever=vectorstore.as_retriever(
        search_type="similarity",  # or "mmr" for diversity
        search_kwargs={"k": 5}  # Retrieve top 5 chunks
    ),
    return_source_documents=True,
    chain_type_kwargs={"prompt": PROMPT}
)

print("=" * 80)
print("✨ RAG SYSTEM READY!")
print("=" * 80)


# ========== MAIN QUERY FUNCTION ==========
def ask_question(question, show_sources=True, show_tokens=True):
    """
    Ask a question and get an answer with optional source display.
    
    Args:
        question: The question to ask
        show_sources: Whether to display source chunks
        show_tokens: Whether to display token usage stats
    """
    print(f"\n{'='*80}")
    print(f"❓ QUESTION: {question}")
    print("=" * 80)
    
    # Track token usage
    with get_openai_callback() as cb:
        result = qa_chain.invoke({"query": question})
    
    # Display answer
    print(f"\n💡 ANSWER:")
    print("-" * 80)
    print(word_wrap(result['result']))
    print("-" * 80)
    
    # Display sources if requested
    if show_sources and result['source_documents']:
        print(f"\n📚 SOURCES ({len(result['source_documents'])} chunks used):")
        for i, doc in enumerate(result['source_documents'], 1):
            page = doc.metadata.get('page', 'Unknown')
            print(f"\n[Source {i} - Page {page}]")
            print(word_wrap(doc.page_content[:300] + "...", 100))
    
    # Display token usage if requested
    if show_tokens:
        print(f"\n📊 TOKEN USAGE:")
        print(f"   - Total Tokens: {cb.total_tokens}")
        print(f"   - Prompt Tokens: {cb.prompt_tokens}")
        print(f"   - Completion Tokens: {cb.completion_tokens}")
        print(f"   - Total Cost: ${cb.total_cost:.6f}")
    
    print("\n" + "=" * 80)
    return result


# ========== SIMILARITY SEARCH FUNCTION ==========
def search_similar(query, k=3):
    """
    Search for similar chunks without generating an answer.
    Useful for understanding what context the system has access to.
    """
    print(f"\n{'='*80}")
    print(f"🔍 SEARCHING FOR: '{query}'")
    print("=" * 80)
    
    results = vectorstore.similarity_search(query, k=k)
    
    for i, doc in enumerate(results, 1):
        page = doc.metadata.get('page', 'Unknown')
        print(f"\n[Result {i} - Page {page}]")
        print(word_wrap(doc.page_content, 100))
        print("-" * 80)
    
    return results


# ========== INTERACTIVE MODE ==========
def interactive_mode():
    """Run an interactive Q&A session."""
    print("\n🎯 EXAMPLE QUESTIONS:")
    example_questions = [
        "What are the steps to classify an image?",
        "What procedures should I follow for fossil identification?",
        "What quality control measures are mentioned?",
        "How should I prepare images before classification?",
        "What are the main categories for classification?"
    ]
    
    for i, q in enumerate(example_questions, 1):
        print(f"   {i}. {q}")
    
    print("\n💡 COMMANDS:")
    print("   - Type your question to get an answer")
    print("   - 'search <query>' to find similar chunks without answer")
    print("   - 'quit' or 'exit' to stop")
    
    while True:
        print("\n" + "=" * 80)
        user_input = input("🔍 Your question: ").strip()
        
        if user_input.lower() in ['quit', 'exit', 'q']:
            print("\n👋 Goodbye!")
            break
        
        if not user_input:
            print("❌ Please enter a valid question.")
            continue
        
        # Handle search command
        if user_input.lower().startswith('search '):
            query = user_input[7:].strip()
            search_similar(query, k=3)
        else:
            # Regular question
            ask_question(user_input, show_sources=True, show_tokens=True)


# ========== MAIN EXECUTION ==========
if __name__ == "__main__":
    # Example usage
    print("\n🚀 Running example query...\n")
    
    # Example question
    ask_question(
        "What is the output format for classification results? Give proper JSON structure.",
        show_sources=True,
        show_tokens=True
    )
    
    # Start interactive mode
    print("\n" + "=" * 80)
    response = input("\n▶️  Start interactive mode? (y/n): ").strip().lower()
    if response == 'y':
        interactive_mode()
    else:
        print("✅ Done! Run this script again to ask more questions.")