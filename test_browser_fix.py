#!/usr/bin/env python3
"""
Test script to verify browser session management fixes
"""
import time
import threading
from browser import create_stealth_driver, cleanup_browser_data

def test_browser_creation():
    """Test creating multiple browser instances sequentially"""
    print("🧪 Testing sequential browser creation...")
    
    for i in range(3):
        print(f"\n--- Test {i+1} ---")
        try:
            driver = create_stealth_driver(headless=True, max_retries=3)
            print(f"✅ Browser {i+1} created successfully")
            
            # Simulate some work
            driver.get("https://www.google.com")
            time.sleep(1)
            
            # Clean up
            cleanup_browser_data(driver)
            driver.quit()
            print(f"✅ Browser {i+1} cleaned up successfully")
            
        except Exception as e:
            print(f"❌ Browser {i+1} failed: {e}")
            return False
    
    return True

def test_concurrent_browser_creation():
    """Test creating browser instances concurrently (should be serialized by lock)"""
    print("\n🧪 Testing concurrent browser creation (should be serialized)...")
    
    results = []
    
    def create_browser(thread_id):
        try:
            print(f"🔄 Thread {thread_id} attempting to create browser...")
            driver = create_stealth_driver(headless=True, max_retries=3)
            print(f"✅ Thread {thread_id} created browser successfully")
            
            # Simulate some work
            driver.get("https://www.google.com")
            time.sleep(0.5)
            
            # Clean up
            cleanup_browser_data(driver)
            driver.quit()
            print(f"✅ Thread {thread_id} cleaned up successfully")
            results.append(True)
            
        except Exception as e:
            print(f"❌ Thread {thread_id} failed: {e}")
            results.append(False)
    
    # Create multiple threads
    threads = []
    for i in range(3):
        thread = threading.Thread(target=create_browser, args=(i+1,))
        threads.append(thread)
        thread.start()
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    success_count = sum(results)
    print(f"\n📊 Concurrent test results: {success_count}/{len(results)} successful")
    return success_count == len(results)

def main():
    print("🚀 Starting browser session management tests...")
    
    # Test 1: Sequential creation
    if not test_browser_creation():
        print("❌ Sequential test failed!")
        return
    
    # Test 2: Concurrent creation
    if not test_concurrent_browser_creation():
        print("❌ Concurrent test failed!")
        return
    
    print("\n🎉 All tests passed! Browser session management is working correctly.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⏹️ Tests interrupted by user.")
    except Exception as e:
        print(f"\n💥 Test suite failed with error: {e}")
