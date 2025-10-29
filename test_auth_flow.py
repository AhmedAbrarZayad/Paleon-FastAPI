"""
Test the complete authentication and classification flow
"""
import requests
import base64
import json
import time
from pathlib import Path

# Configuration
BASE_URL = "http://localhost:8000"
TEST_EMAIL = "ahmedabrarzayad@gmail.com"
TEST_PASSWORD = "testpassword123"
TEST_USERNAME = "testuser"

def print_section(title):
    """Print a formatted section header"""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)

def test_register():
    """Test user registration"""
    print_section("1. TESTING USER REGISTRATION")
    
    url = f"{BASE_URL}/auth/register"
    data = {
        "email": TEST_EMAIL,
        "username": TEST_USERNAME,
        "password": TEST_PASSWORD
    }
    
    print(f"POST {url}")
    print(f"Data: {json.dumps(data, indent=2)}")
    
    response = requests.post(url, json=data)
    
    print(f"\nStatus Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 201:
        print("✅ Registration successful!")
        return response.json()["access_token"]
    elif response.status_code == 400 and "already registered" in response.json()["detail"]:
        print("⚠️  User already exists, trying login instead...")
        return None
    else:
        print("❌ Registration failed!")
        return None

def test_login():
    """Test user login"""
    print_section("2. TESTING USER LOGIN")
    
    url = f"{BASE_URL}/auth/login"
    data = {
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    }
    
    print(f"POST {url}")
    print(f"Data: {json.dumps(data, indent=2)}")
    
    response = requests.post(url, json=data)
    
    print(f"\nStatus Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 200:
        print("✅ Login successful!")
        return response.json()["access_token"]
    else:
        print("❌ Login failed!")
        return None

def test_get_me(token):
    """Test getting current user info"""
    print_section("3. TESTING GET CURRENT USER (/auth/me)")
    
    url = f"{BASE_URL}/auth/me"
    headers = {"Authorization": f"Bearer {token}"}
    
    print(f"GET {url}")
    print(f"Headers: Authorization: Bearer {token[:20]}...")
    
    response = requests.get(url, headers=headers)
    
    print(f"\nStatus Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 200:
        print("✅ Got user info successfully!")
        return response.json()
    else:
        print("❌ Failed to get user info!")
        return None

def test_create_api_key(token):
    """Test creating an API key"""
    print_section("4. TESTING CREATE API KEY")
    
    url = f"{BASE_URL}/auth/api-keys"
    headers = {"Authorization": f"Bearer {token}"}
    data = {"name": "Test API Key"}
    
    print(f"POST {url}")
    print(f"Data: {json.dumps(data, indent=2)}")
    
    response = requests.post(url, headers=headers, json=data)
    
    print(f"\nStatus Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 200:
        print("✅ API key created successfully!")
        print(f"🔑 API Key: {response.json().get('key', 'N/A')}")
        return response.json()
    else:
        print("❌ Failed to create API key!")
        return None

def get_test_images():
    """Get available test images from backend directory"""
    test_images = [
        Path("test_image.jpeg"),
        Path("test_image_2.jpeg"),
        Path("test_image_3.jpeg"),
    ]
    
    # Filter only existing images
    existing_images = [img for img in test_images if img.exists()]
    
    if not existing_images:
        print("⚠️  No test images found in backend directory!")
        print("Expected: test_image.jpeg, test_image_2.jpeg, test_image_3.jpeg")
        return []
    
    print(f"📸 Found {len(existing_images)} test image(s):")
    for img in existing_images:
        print(f"   - {img.name}")
    
    return existing_images

def test_classify_async(token, use_multiple=False):
    """Test async image classification"""
    print_section("5. TESTING ASYNC CLASSIFICATION")
    
    url = f"{BASE_URL}/classify-async/"
    headers = {"Authorization": f"Bearer {token}"}
    
    # Get test images
    test_images = get_test_images()
    
    if not test_images:
        print("❌ No test images available. Skipping classification test.")
        return None
    
    # Use one image or multiple based on parameter
    images_to_upload = test_images[:3] if use_multiple else test_images[:1]
    
    print(f"POST {url}")
    print(f"Uploading {len(images_to_upload)} image(s)...")
    
    # Prepare files for upload
    files = []
    for img_path in images_to_upload:
        files.append(
            ('image_files', (img_path.name, open(img_path, 'rb'), 'image/jpeg'))
        )
    
    try:
        response = requests.post(url, headers=headers, files=files)
        
        # Close all file handles
        for _, (_, file_handle, _) in files:
            file_handle.close()
        
        print(f"\nStatus Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Response: {json.dumps(result, indent=2)}")
            print("✅ Classification job submitted!")
            return result.get("job_id")
        elif response.status_code == 429:
            print("⚠️  Rate limit exceeded!")
            print(f"Response: {json.dumps(response.json(), indent=2)}")
            return None
        else:
            print(f"❌ Classification failed!")
            print(f"Response: {response.text}")
            return None
    
    except Exception as e:
        # Make sure files are closed even on error
        for _, (_, file_handle, _) in files:
            try:
                file_handle.close()
            except:
                pass
        raise e

def test_check_result(token, job_id):
    """Test checking classification result"""
    print_section("6. TESTING CHECK RESULT")
    
    url = f"{BASE_URL}/result/{job_id}"
    headers = {"Authorization": f"Bearer {token}"}
    
    print(f"GET {url}")
    print("Waiting for result (checking every 3 seconds)...")
    
    max_attempts = 10
    for attempt in range(1, max_attempts + 1):
        print(f"\nAttempt {attempt}/{max_attempts}...")
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            result = response.json()
            status = result.get("status")
            
            print(f"Status: {status}")
            
            if status == "completed":
                print(f"✅ Classification completed!")
                print(f"Result: {json.dumps(result.get('result'), indent=2)}")
                return result
            elif status == "failed":
                print(f"❌ Classification failed!")
                print(f"Error: {result.get('error')}")
                return result
            elif status == "processing":
                print("⏳ Still processing...")
                time.sleep(3)
            else:
                print(f"Status: {status}")
                time.sleep(3)
        else:
            print(f"❌ Failed to check result: {response.status_code}")
            print(f"Response: {response.text}")
            return None
    
    print("⚠️  Timeout waiting for result")
    return None

def test_get_jobs(token):
    """Test getting user's classification jobs"""
    print_section("7. TESTING GET USER JOBS")
    
    url = f"{BASE_URL}/jobs"
    headers = {"Authorization": f"Bearer {token}"}
    
    print(f"GET {url}")
    
    response = requests.get(url, headers=headers)
    
    print(f"\nStatus Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 200:
        print("✅ Got user jobs successfully!")
        return response.json()
    else:
        print("❌ Failed to get user jobs!")
        return None

def test_rate_limiting(token):
    """Test rate limiting (Free tier = 3 requests/day)"""
    print_section("8. TESTING RATE LIMITING")
    
    print("Free tier allows 3 requests per day")
    print("Making 4 consecutive requests to test rate limiting...")
    
    for i in range(1, 5):
        print(f"\n--- Request {i}/4 ---")
        job_id = test_classify_async(token, use_multiple=False)
        
        if job_id:
            print(f"✅ Request {i} accepted (Job ID: {job_id})")
        else:
            print(f"⚠️  Request {i} rejected (likely rate limited)")
        
        time.sleep(1)

def test_classify_multiple_images(token):
    """Test classification with multiple images"""
    print_section("5b. TESTING MULTIPLE IMAGES CLASSIFICATION")
    
    test_images = get_test_images()
    
    if len(test_images) < 2:
        print("⚠️  Need at least 2 images for this test. Skipping.")
        return None
    
    print(f"Will upload all {len(test_images)} images together...")
    return test_classify_async(token, use_multiple=True)

def main():
    """Run all tests"""
    print("\n" + "🚀" * 30)
    print("  PALEON BACKEND - AUTHENTICATION & CLASSIFICATION TEST")
    print("🚀" * 30)
    
    print(f"\nBase URL: {BASE_URL}")
    print(f"Test Email: {TEST_EMAIL}")
    print(f"Test Username: {TEST_USERNAME}")
    
    # Step 1: Register or Login
    token = test_register()
    if not token:
        token = test_login()
    
    if not token:
        print("\n❌ FAILED: Could not authenticate")
        return
    
    print(f"\n✅ Authentication successful!")
    print(f"🔑 Access Token: {token[:30]}...")
    
    # Step 2: Get user info
    user_info = test_get_me(token)
    if user_info:
        print(f"👤 User ID: {user_info.get('user_id')}")
        print(f"👤 Tier: {user_info.get('tier')}")
    
    # Step 3: Create API key
    api_key_info = test_create_api_key(token)
    
    # Step 4: Test single image classification
    job_id = test_classify_async(token, use_multiple=False)
    
    if job_id:
        # Step 5: Check result
        test_check_result(token, job_id)
    
    # Step 4b: Test multiple images (optional)
    print("\n💡 Testing with multiple images...")
    job_id_multi = test_classify_multiple_images(token)
    
    if job_id_multi:
        test_check_result(token, job_id_multi)
    
    # Step 6: Get all jobs
    test_get_jobs(token)
    
    # Step 7: Test rate limiting (optional - uncomment if you want to test)
    # test_rate_limiting(token)
    
    print("\n" + "="*60)
    print("  ✅ ALL TESTS COMPLETED")
    print("="*60)

if __name__ == "__main__":
    try:
        main()
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Could not connect to FastAPI server")
        print("Please make sure the server is running on http://localhost:8000")
        print("\nStart server with: fastapi dev app/main.py")
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
