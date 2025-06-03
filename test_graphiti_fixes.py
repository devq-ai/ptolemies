#!/usr/bin/env python3
"""
Test script to verify the Graphiti service fixes.
This script tests the corrected AddEpisodeResults object access patterns.
"""

import asyncio
import requests
import json
from datetime import datetime, timezone

def test_episode_processing():
    """Test the episode processing endpoint with the fixed result access."""
    
    url = "http://localhost:8001/episodes"
    
    # Test data
    episode_data = {
        "content": "Alice works at OpenAI as a software engineer. She collaborates with Bob on machine learning projects.",
        "metadata": {
            "source": "test_conversation",
            "timestamp": datetime.now(timezone.utc).isoformat()
        },
        "group_id": "test_group"
    }
    
    print("🧪 Testing episode processing...")
    print(f"📤 Sending request to: {url}")
    print(f"📋 Request data: {json.dumps(episode_data, indent=2)}")
    
    try:
        response = requests.post(url, json=episode_data, timeout=30)
        
        print(f"📨 Response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Episode processing successful!")
            print(f"📄 Response data:")
            print(f"  - Episode ID: {result['episode_id']}")
            print(f"  - Entities found: {len(result['entities'])}")
            print(f"  - Relationships found: {len(result['relationships'])}")
            print(f"  - Processing time: {result['processing_time']:.2f}s")
            
            # Print details about entities and relationships
            if result['entities']:
                print(f"🔍 Entities:")
                for i, entity in enumerate(result['entities']):
                    print(f"  {i+1}. {entity['name']} (ID: {entity['id']}, Type: {entity['type']})")
            
            if result['relationships']:
                print(f"🔗 Relationships:")
                for i, rel in enumerate(result['relationships']):
                    print(f"  {i+1}. {rel['source']} -> {rel['target']} ({rel['type']})")
                    if 'fact' in rel:
                        print(f"     Fact: {rel['fact']}")
            
            return True
        else:
            print(f"❌ Episode processing failed with status {response.status_code}")
            print(f"📄 Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_health_check():
    """Test the health check endpoint."""
    
    url = "http://localhost:8001/health"
    
    print("🏥 Testing health check...")
    
    try:
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Health check successful!")
            print(f"  - Status: {result['status']}")
            print(f"  - Graphiti ready: {result['graphiti_ready']}")
            print(f"  - Neo4j connected: {result['neo4j_connected']}")
            return True
        else:
            print(f"❌ Health check failed with status {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def test_entity_search():
    """Test the entity search endpoint with the fixed search method."""
    
    url = "http://localhost:8001/entities/search"
    params = {
        "query": "Alice",
        "limit": 5
    }
    
    print("🔎 Testing entity search...")
    
    try:
        response = requests.get(url, params=params, timeout=15)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Entity search successful!")
            print(f"  - Query: '{result['query']}'")
            print(f"  - Results found: {result['total_count']}")
            
            if result['results']:
                print(f"🔍 Search results:")
                for i, entity in enumerate(result['results']):
                    print(f"  {i+1}. {entity['name']} (ID: {entity['id']}, Type: {entity['type']})")
            
            return True
        else:
            print(f"❌ Entity search failed with status {response.status_code}")
            print(f"📄 Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Entity search error: {e}")
        return False

def main():
    """Run all tests."""
    print("🚀 Starting Graphiti Service Fix Tests")
    print("=" * 60)
    
    # Check if service is running
    print("🔍 Checking if Graphiti service is running...")
    try:
        response = requests.get("http://localhost:8001/", timeout=5)
        if response.status_code != 200:
            print("❌ Graphiti service is not running on localhost:8001")
            print("💡 Start the service with: python -m src.ptolemies.integrations.graphiti.graphiti_service")
            return 1
        print("✅ Graphiti service is running")
    except Exception as e:
        print(f"❌ Cannot connect to Graphiti service: {e}")
        print("💡 Start the service with: python -m src.ptolemies.integrations.graphiti.graphiti_service")
        return 1
    
    print()
    
    # Run tests
    tests = [
        ("Health Check", test_health_check),
        ("Episode Processing", test_episode_processing),
        ("Entity Search", test_entity_search),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"🧪 Running: {test_name}")
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ Test '{test_name}' failed with exception: {e}")
            results.append((test_name, False))
        print()
    
    # Summary
    print("📋 Test Results Summary")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{test_name:.<30} {status}")
        if success:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! The AddEpisodeResults fixes are working correctly.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Check the error messages above.")
        return 1

if __name__ == "__main__":
    exit(main())