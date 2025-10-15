"""
COMPLETE WORKFLOW: RAG-Enhanced Image Classification System

Step 1: Extract specifications from PDF using RAG
Step 2: Use specifications to classify images with OpenAI Vision API
Step 3: Format output according to extracted specifications
"""

from dotenv import load_dotenv
import os
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import Chroma
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from openai import OpenAI
import base64
import json
from pathlib import Path
# Load environment variables
load_dotenv("C:\\Users\\ahmed\\Documents\\Flutter\\Paleon\\backend\\.env")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PERSIST_DIR = "./fossils-db"
COLLECTION_NAME = "fossils_collection"

# ========== STEP 1: RAG SYSTEM FOR SPECIFICATION EXTRACTION ==========

class SpecificationExtractor:
    """Extract classification specifications from PDF using RAG."""
    
    def __init__(self):
        # Initialize embeddings
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-large",
            openai_api_key=OPENAI_API_KEY
        )
        
        # Load vector store
        self.vectorstore = Chroma(
            persist_directory=PERSIST_DIR,
            embedding_function=self.embeddings,
            collection_name=COLLECTION_NAME
        )
        
        # Initialize LLM
        self.llm = ChatOpenAI(
            model="gpt-4o",
            temperature=0,
            openai_api_key=OPENAI_API_KEY
        )
        
        # Refined prompt for extracting specifications
        prompt_template = """You are extracting precise specifications from a master prompt pdf for an image classification system.

Context from Documentation:
{context}

Question: {question}

CRITICAL: Extract EXACT requirements as they will be used programmatically.
- For formats: provide exact field names, data types, and structure
- For criteria: provide specific decision rules and thresholds
- For procedures: provide step-by-step logic
- Use structured formatting (lists, tables) for clarity
- If information is missing, explicitly state what's unclear

Provide implementation-ready details:"""

        PROMPT = PromptTemplate(
            template=prompt_template,
            input_variables=["context", "question"]
        )
        
        # Create QA chain
        self.qa_chain = RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type="stuff",
            retriever=self.vectorstore.as_retriever(
                search_type="similarity",
                search_kwargs={"k": 6}
            ),
            return_source_documents=True,
            chain_type_kwargs={"prompt": PROMPT}
        )
    
    def extract_classification_prompt(self):
        """
        Extract the complete classification instructions to be used with Vision API.
        This is the KEY method for your workflow.
        """

        query = """
        Based on this documentation, create a COMPLETE and DETAILED prompt that I can use with OpenAI's Vision API to classify images.

        ***CRITICAL INSTRUCTION FOR CLASSIFICATION PRIORITIZATION***
        The prompt MUST include an overriding instruction: **"You prioritize project-provided taxonomies, BUT you may overrule a single, rigid negative constraint (e.g., 'must not have X') if the overall visual evidence, supported by general paleontological knowledge, creates a high-probability match for a family otherwise excluded (e.g., ruling out Mosasauridae). When classification rules conflict with visual evidence, assign probabilities based on the visual fit and clearly mark confidence as 'low' or 'medium' due to rule conflict."**

        The prompt should include:
        1. What to look for in the image (visual features, characteristics)
        2. Get the Decision Funnel
        3. ALL possible classification categories with their exact definitions
        4. Step-by-step classification logic and decision criteria
        5. How to handle edge cases or uncertain classifications
        6. The EXACT output format (JSON structure with all required fields)
        7. Any confidence scoring or validation rules

        Format this as a single, ready-to-use prompt that can be sent directly to GPT-4 Vision.
        """
        
        result = self.qa_chain.invoke({"query": query})
        return result['result']
    
    def extract_output_format(self):
        """Extract the exact output format specification."""
        query = """
        What is the EXACT JSON output format for classification results?
        Provide a JSON schema or example showing:
        - All required fields with exact names
        - Data types for each field
        - Nested structures if any
        - Any validation rules
        """
        
        result = self.qa_chain.invoke({"query": query})
        return result['result']


# ========== STEP 2: IMAGE CLASSIFIER USING EXTRACTED SPECIFICATIONS ==========

class ImageClassifier:
    """Classify images using OpenAI Vision API with RAG-extracted specifications."""
    
    def __init__(self, classification_prompt, output_format):
        """
        Args:
            classification_prompt: The prompt extracted from RAG system
            output_format: The output format specification extracted from RAG
        """
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.classification_prompt = classification_prompt
        self.output_format = output_format
        
    def encode_image(self, image_path):
        """Encode image to base64."""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    
    def classify_image(self, image_paths, additional_context=""):
        """
        Classify one or multiple images of the same fossil using extracted specifications.
        
        Args:
            image_paths: Single path (str) or list of paths for multiple views of same fossil
            additional_context: Any additional context or metadata about the fossil
        
        Returns:
            dict: Classification results in the specified format
        """
        
        # Normalize input to list
        if isinstance(image_paths, str):
            image_paths = [image_paths]
        
        # Prepare the full prompt with context about multiple images
        multi_image_context = ""
        if len(image_paths) > 1:
            multi_image_context = f"\n\nNOTE: You are being provided with {len(image_paths)} images of the SAME fossil from different angles/views. Analyze ALL images together to make a comprehensive classification decision.\n"
        
        full_prompt = f"""
{self.classification_prompt}

{additional_context}
{multi_image_context}

IMPORTANT: Return your response in the following format:
{self.output_format}
Don't add any extra commentary or explanation.
Ensure the output is valid JSON that can be parsed programmatically.
"""
        
        # Build content array with text and all images
        content = [{"type": "text", "text": full_prompt}]
        
        # Add all images to the content
        for idx, image_path in enumerate(image_paths):
            if image_path.startswith('http'):
                # URL image
                content.append({
                    "type": "image_url",
                    "image_url": {"url": image_path}
                })
            else:
                # Local file - encode to base64
                base64_image = self.encode_image(image_path)
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_image}",
                        "detail": "high"  # Use "high" for detailed analysis
                    }
                })
        
        # Make API call with all images
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": content
                }
            ],
            max_tokens=2000,
            temperature=0,
            response_format={"type": "json_object"}
        )
        
        # Parse response
        result_text = response.choices[0].message.content
        print("Raw response:", result_text)
        # Try to extract JSON if wrapped in markdown
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0].strip()
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0].strip()
        
        # Parse JSON
        try:
            result = json.loads(result_text)
            # Add metadata about how many images were used
            result['_metadata'] = {
                'num_images_analyzed': len(image_paths),
                'image_paths': image_paths
            }
        except json.JSONDecodeError:
            result = {
                "raw_response": result_text, 
                "error": "Failed to parse JSON",
                '_metadata': {
                    'num_images_analyzed': len(image_paths),
                    'image_paths': image_paths
                }
            }
        
        return result


# ========== STEP 3: COMPLETE WORKFLOW ==========

def main():
    """
    Main workflow demonstrating the complete system:
    1. Extract specifications from PDF
    2. Classify images using extracted specifications
    """
    
    print("="*80)
    print("🚀 COMPLETE CLASSIFICATION WORKFLOW")
    print("="*80)
    
    # STEP 1: Extract specifications from PDF
    print("\n📚 STEP 1: Extracting classification specifications from PDF...")
    print("-"*80)
    
    extractor = SpecificationExtractor()
    
    print("Extracting classification prompt...")
    classification_prompt = extractor.extract_classification_prompt()
    
    print("Extracting output format...")
    output_format = extractor.extract_output_format()
    
    print("\n✅ Specifications extracted!")
    print("\n📝 CLASSIFICATION PROMPT:")
    print("-"*80)
    print(classification_prompt[:500] + "...\n")
    
    print("📋 OUTPUT FORMAT:")
    print("-"*80)
    print(output_format[:300] + "...\n")
    
    # Optional: Save specifications for review
    save_specs = input("💾 Save extracted specifications to file? (y/n): ").strip().lower()
    if save_specs == 'y':
        with open("classification_specifications.txt", "w", encoding="utf-8") as f:
            f.write("CLASSIFICATION PROMPT:\n")
            f.write("="*80 + "\n")
            f.write(classification_prompt + "\n\n")
            f.write("OUTPUT FORMAT:\n")
            f.write("="*80 + "\n")
            f.write(output_format + "\n")
        print("✅ Specifications saved to classification_specifications.txt")
    
    # STEP 2: Classify images
    print("\n" + "="*80)
    print("🖼️ STEP 2: Classifying images...")
    print("-"*80)
    
    classifier = ImageClassifier(classification_prompt, output_format)
    IMAGE_PATHS = [
        "app/services/tooth-1.jpeg",
        "app/services/tooth-2.jpeg",
        "app/services/tooth-3.jpeg"
    ]
    result = classifier.classify_image(IMAGE_PATHS)
    print("\n📤 CLASSIFICATION RESULT:")
    print("="*80)
    print(json.dumps(result, indent=2))
    print("="*80)
    print("\n✅ Workflow complete!")
    print("="*80)
    """
    # Get image path from user
    image_input = input("\nEnter image path or URL (or press Enter to skip): ").strip()
    
    if image_input:
        # Optional: Add metadata or context
        context = input("Add any additional context about the image (optional): ").strip()
        
        print(f"\n🔍 Classifying: {image_input}")
        result = classifier.classify_image(image_input, context)
        
        print("\n📤 CLASSIFICATION RESULT:")
        print("="*80)
        print(json.dumps(result, indent=2))
        print("="*80)
        
        # Save result
        save_result = input("\n💾 Save result to file? (y/n): ").strip().lower()
        if save_result == 'y':
            output_file = "classification_result.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2)
            print(f"✅ Result saved to {output_file}")
    
    print("\n✅ Workflow complete!")
    print("="*80)
    """



if __name__ == "__main__":
    main()