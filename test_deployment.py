#!/usr/bin/env python3
"""
Simple test script to verify the FastAPI deployment
"""
import requests
import json

def test_api_endpoints():
    """Test the deployed API endpoints"""
    base_url = "https://backend-jdoerthzc-oluwafemis-projects-6b4a2351.vercel.app"
    
    print(f"Testing API at: {base_url}")
    print("=" * 50)
    
    # Test root endpoint
    try:
        print("Testing GET /")
        response = requests.get(f"{base_url}/", timeout=10)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2)}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Error testing root endpoint: {e}")
    
    print("-" * 30)
    
    # Test health endpoint
    try:
        print("Testing GET /health")
        response = requests.get(f"{base_url}/health", timeout=10)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2)}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Error testing health endpoint: {e}")
    
    print("-" * 30)
    
    # Test search endpoint (should return 422 for missing data)
    try:
        print("Testing POST /search (should return 422)")
        response = requests.post(f"{base_url}/search", timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:200]}...")
    except Exception as e:
        print(f"Error testing search endpoint: {e}")

if __name__ == "__main__":
    test_api_endpoints()
