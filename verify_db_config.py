#!/usr/bin/env python3
"""
Verify database configuration matches .env file
"""
import os
import sys

def load_env_file(filepath=".env"):
    """Load environment variables from .env file."""
    env_vars = {}
    if not os.path.exists(filepath):
        return env_vars
    
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env_vars[key] = value
    
    return env_vars

def verify_configuration():
    """Verify the current configuration."""
    print("🔍 Verifying Ptolemies Database Configuration")
    print("=" * 50)
    
    # Load .env file
    env_vars = load_env_file()
    
    # Check SurrealDB configuration
    print("\n📊 SurrealDB Configuration:")
    surrealdb_config = {
        'SURREALDB_URL': env_vars.get('SURREALDB_URL', 'NOT SET'),
        'SURREALDB_USERNAME': env_vars.get('SURREALDB_USERNAME', 'NOT SET'),
        'SURREALDB_PASSWORD': env_vars.get('SURREALDB_PASSWORD', 'NOT SET'),
        'SURREALDB_NAMESPACE': env_vars.get('SURREALDB_NAMESPACE', 'NOT SET'),
        'SURREALDB_DATABASE': env_vars.get('SURREALDB_DATABASE', 'NOT SET'),
    }
    
    for key, value in surrealdb_config.items():
        print(f"   {key}: {value}")
    
    # Check Neo4j configuration
    print("\n🕸️  Neo4j Configuration:")
    neo4j_config = {
        'NEO4J_URI': env_vars.get('NEO4J_URI', 'NOT SET'),
        'NEO4J_USERNAME': env_vars.get('NEO4J_USERNAME', 'NOT SET'),
        'NEO4J_PASSWORD': env_vars.get('NEO4J_PASSWORD', 'NOT SET'),
        'NEO4J_DATABASE': env_vars.get('NEO4J_DATABASE', 'NOT SET'),
    }
    
    for key, value in neo4j_config.items():
        print(f"   {key}: {value}")
    
    # Check Redis configuration
    print("\n🔄 Redis Configuration:")
    redis_config = {
        'UPSTASH_REDIS_REST_URL': env_vars.get('UPSTASH_REDIS_REST_URL', 'NOT SET'),
        'UPSTASH_REDIS_REST_TOKEN': env_vars.get('UPSTASH_REDIS_REST_TOKEN', 'NOT SET'),
    }
    
    for key, value in redis_config.items():
        if 'TOKEN' in key and value != 'NOT SET':
            print(f"   {key}: ***HIDDEN***")
        else:
            print(f"   {key}: {value}")
    
    # Verify correctness
    print("\n✅ Configuration Verification:")
    
    correct_namespace = env_vars.get('SURREALDB_NAMESPACE') == 'ptolemies'
    correct_database = env_vars.get('SURREALDB_DATABASE') == 'knowledge'
    
    if correct_namespace and correct_database:
        print("   ✅ SurrealDB configuration is CORRECT")
        print("      - Namespace: ptolemies ✓")
        print("      - Database: knowledge ✓")
    else:
        print("   ❌ SurrealDB configuration needs attention:")
        if not correct_namespace:
            print(f"      - Namespace should be 'ptolemies', found: {env_vars.get('SURREALDB_NAMESPACE', 'NOT SET')}")
        if not correct_database:
            print(f"      - Database should be 'knowledge', found: {env_vars.get('SURREALDB_DATABASE', 'NOT SET')}")
    
    # Check for potential issues
    print("\n🔍 Potential Issues:")
    
    issues = []
    
    if env_vars.get('SURREALDB_URL', '').startswith('ws://localhost'):
        issues.append("SurrealDB is configured for localhost - ensure server is running")
    
    if env_vars.get('NEO4J_URI', '').startswith('bolt://localhost'):
        issues.append("Neo4j is configured for localhost - ensure server is running")
    
    if not env_vars.get('OPENAI_API_KEY'):
        issues.append("OPENAI_API_KEY not found - embeddings will not work")
    
    if issues:
        for issue in issues:
            print(f"   ⚠️  {issue}")
    else:
        print("   ✅ No obvious configuration issues detected")
    
    # Show environment loading status
    print("\n📋 Environment Status:")
    env_file_exists = os.path.exists('.env')
    print(f"   .env file exists: {'✅' if env_file_exists else '❌'}")
    print(f"   Variables loaded: {len(env_vars)}")
    
    return correct_namespace and correct_database

if __name__ == "__main__":
    result = verify_configuration()
    if result:
        print("\n🎉 Configuration is ready for use!")
        sys.exit(0)
    else:
        print("\n⚠️  Configuration needs to be fixed before proceeding")
        sys.exit(1)