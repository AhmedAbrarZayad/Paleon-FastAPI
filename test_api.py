"""
Quick test script for the Fossil Classification API.

Usage:
    python test_api.py
"""

import requests
import json
from pathlib import Path

# API endpoint
BASE_URL = "http://localhost:8000"

def test_health_check():
    """Test if server is running."""
    print("\n" + "="*60)
    print("TEST 1: Health Check")
    print("="*60)
    
    try:
        response = requests.get(f"{BASE_URL}/")
        print(f"✅ Status: {response.status_code}")
        print(f"✅ Response: {json.dumps(response.json(), indent=2)}")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        print("💡 Make sure server is running: uvicorn app.main:app --reload")
        return False

def test_classification_single_image():
    """Test classification with single image."""
    print("\n" + "="*60)
    print("TEST 2: Single Image Classification")
    print("="*60)
    
    # Find test image
    test_images = [
        "app/services/tooth-1.jpeg",
        "app/services/tooth-2.jpeg",
        "app/services/tooth-3.jpeg",
    ]
    
    test_image = None
    for img in test_images:
        if Path(img).exists():
            test_image = img
            break
    
    if not test_image:
        print("❌ No test images found!")
        print("💡 Add test images to app/services/")
        return False
    
    print(f"📸 Using image: {test_image}")
    
    try:
        with open(test_image, "rb") as f:
            files = {"image_files": f}
            response = requests.post(
                f"{BASE_URL}/fossil-image/",
                files=files,
                timeout=60  # 60 seconds timeout
            )
        
        print(f"✅ Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("\n📊 CLASSIFICATION RESULT:")
            print("-"*60)
            print(json.dumps(result, indent=2))
            print("-"*60)
            
            # Extract key info
            if result.get("success"):
                classification = result.get("classification", {})
                print(f"\n🦴 Fossil Name: {classification.get('fossil_name', 'Unknown')}")
                print(f"🔬 Confidence: {classification.get('confidence', 'Unknown')}")
                print(f"⏱️  Processing Time: {result['metadata']['processing_time_ms']}ms")
            
            return True
        else:
            print(f"❌ Error: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ Request timeout (>60s)")
        print("💡 First request is slow (initializing RAG). Try again!")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_classification_multiple_images():
    """Test classification with multiple images."""
    print("\n" + "="*60)
    print("TEST 3: Multiple Image Classification")
    print("="*60)
    
    # Find test images
    test_images = [
        "app/services/tooth-1.jpeg",
        "app/services/tooth-2.jpeg",
        "app/services/tooth-3.jpeg",
    ]
    
    existing_images = [img for img in test_images if Path(img).exists()]
    
    if len(existing_images) < 2:
        print("⚠️  Need at least 2 test images!")
        print("💡 Add test images to app/services/")
        return False
    
    print(f"📸 Using {len(existing_images)} images:")
    for img in existing_images:
        print(f"   - {img}")
    
    try:
        files = [("image_files", open(img, "rb")) for img in existing_images]
        
        response = requests.post(
            f"{BASE_URL}/fossil-image/",
            files=files,
            timeout=60
        )
        
        # Close all files
        for _, f in files:
            f.close()
        
        print(f"✅ Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("\n📊 CLASSIFICATION RESULT:")
            print("-"*60)
            print(json.dumps(result, indent=2))
            print("-"*60)
            
            if result.get("success"):
                classification = result.get("classification", {})
                print(f"\n🦴 Fossil Name: {classification.get('fossil_name', 'Unknown')}")
                print(f"🔬 Confidence: {classification.get('confidence', 'Unknown')}")
                print(f"📸 Images Analyzed: {result['metadata']['num_images_analyzed']}")
                print(f"⏱️  Processing Time: {result['metadata']['processing_time_ms']}ms")
            
            return True
        else:
            print(f"❌ Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_error_handling():
    """Test error handling."""
    print("\n" + "="*60)
    print("TEST 4: Error Handling (No Images)")
    print("="*60)
    
    try:
        # Send request with no images
        response = requests.post(f"{BASE_URL}/fossil-image/")
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 422:  # Validation error
            print("✅ Server correctly rejects empty request")
            return True
        else:
            print("⚠️  Expected status 422")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Run all tests."""
    print("\n" + "🧪 FOSSIL CLASSIFICATION API - TEST SUITE")
    print("="*60)
    
    results = []
    
    # Test 1: Health check
    results.append(("Health Check", test_health_check()))
    
    if not results[0][1]:
        print("\n❌ Server is not running. Stopping tests.")
        return
    
    # Test 2: Single image
    print("\n⏳ First request may take ~15 seconds (RAG initialization)...")
    results.append(("Single Image", test_classification_single_image()))
    
    # Test 3: Multiple images
    results.append(("Multiple Images", test_classification_multiple_images()))
    
    # Test 4: Error handling
    results.append(("Error Handling", test_error_handling()))
    
    # Summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status} - {test_name}")
    
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    
    print(f"\nTotal: {passed_count}/{total_count} tests passed")
    
    if passed_count == total_count:
        print("\n🎉 All tests passed!")
    else:
        print("\n⚠️  Some tests failed. Check errors above.")

if __name__ == "__main__":
    main()
