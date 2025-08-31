#!/usr/bin/env python3
"""
Test script for the M3U8 scraper functionality
This script tests the basic functionality without requiring actual anime URLs
"""

import json
import os
from unittest.mock import Mock, patch
from m3u8_scraper import M3U8Scraper


def test_m3u8_scraper_creation():
    """Test M3U8Scraper instance creation"""
    print("🧪 Testing M3U8Scraper instance creation...")
    
    scraper = M3U8Scraper(headless=True, max_retries=2)
    
    assert scraper.headless == True
    assert scraper.max_retries == 2
    assert scraper.driver is None
    
    print("✅ M3U8Scraper instance creation test passed")


def test_context_manager():
    """Test M3U8Scraper context manager functionality"""
    print("🧪 Testing context manager functionality...")
    
    with M3U8Scraper(headless=True) as scraper:
        assert scraper is not None
        assert isinstance(scraper, M3U8Scraper)
    
    # After context exit, driver should be None
    assert scraper.driver is None
    
    print("✅ Context manager test passed")


def test_save_results():
    """Test saving results to JSON file"""
    print("🧪 Testing save_results functionality...")
    
    test_results = {
        "episode1": {
            "video_src": "https://example.com/video1.m3u8",
            "iframe_video": "https://example.com/iframe1.m3u8"
        },
        "episode2": {
            "source_src": "https://example.com/source2.m3u8"
        }
    }
    
    test_filename = "test_m3u8_results.json"
    
    # Create scraper and save results
    with M3U8Scraper() as scraper:
        scraper.save_results(test_results, test_filename)
        
        # Verify file was created
        assert os.path.exists(test_filename)
        
        # Verify content is correct
        with open(test_filename, 'r', encoding='utf-8') as f:
            loaded_results = json.load(f)
        
        assert loaded_results == test_results
    
    # Clean up test file
    if os.path.exists(test_filename):
        os.remove(test_filename)
    
    print("✅ Save results test passed")


def test_extract_video_sources_no_driver():
    """Test _extract_video_sources when driver is None"""
    print("🧪 Testing _extract_video_sources with no driver...")
    
    with M3U8Scraper() as scraper:
        # Manually set driver to None
        scraper.driver = None
        
        sources = scraper._extract_video_sources()
        assert sources == {}
    
    print("✅ Extract video sources (no driver) test passed")


def test_m3u8_scraper_methods():
    """Test that all M3U8Scraper methods exist and are callable"""
    print("🧪 Testing M3U8Scraper method existence...")
    
    with M3U8Scraper() as scraper:
        # Check that all required methods exist
        required_methods = [
            'scrape_episode_m3u8_links',
            'scrape_multiple_episodes',
            'save_results',
            '_extract_video_sources',
            'cleanup'
        ]
        
        for method_name in required_methods:
            assert hasattr(scraper, method_name)
            method = getattr(scraper, method_name)
            assert callable(method)
    
    print("✅ Method existence test passed")


def run_all_tests():
    """Run all test functions"""
    print("🚀 Starting M3U8 Scraper tests...\n")
    
    test_functions = [
        test_m3u8_scraper_creation,
        test_context_manager,
        test_save_results,
        test_extract_video_sources_no_driver,
        test_m3u8_scraper_methods
    ]
    
    passed = 0
    total = len(test_functions)
    
    for test_func in test_functions:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"❌ Test {test_func.__name__} failed: {e}")
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The M3U8 scraper is ready to use.")
    else:
        print("⚠️ Some tests failed. Please check the implementation.")


if __name__ == "__main__":
    run_all_tests()
