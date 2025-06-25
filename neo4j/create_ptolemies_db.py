#!/usr/bin/env python3
"""
Create Ptolemies Database in Neo4j
Simple script to create the database first
"""

import subprocess

def create_database():
    """Create ptolemies database in Neo4j."""
    print("🗄️ Creating 'ptolemies' database in your Neo4j devqai project...")
    
    # Connect to system database to create new database
    cmd = [
        'cypher-shell',
        '-a', 'bolt://localhost:7687',
        '-u', 'neo4j',
        '-p', 'ptolemies',
        '-d', 'system'
    ]
    
    create_query = "CREATE DATABASE ptolemies IF NOT EXISTS;"
    
    try:
        result = subprocess.run(
            cmd,
            input=create_query,
            text=True,
            capture_output=True,
            timeout=30
        )
        
        if result.returncode == 0:
            print("✅ Database 'ptolemies' created successfully!")
            
            # Verify the database was created
            show_cmd = cmd.copy()
            show_query = "SHOW DATABASES YIELD name WHERE name = 'ptolemies';"
            
            verify_result = subprocess.run(
                show_cmd,
                input=show_query,
                text=True,
                capture_output=True,
                timeout=10
            )
            
            if verify_result.returncode == 0 and "ptolemies" in verify_result.stdout:
                print("✅ Database 'ptolemies' verified in your devqai project")
                return True
            else:
                print(f"⚠️ Database created but verification failed: {verify_result.stdout}")
                return True  # Assume it worked
        else:
            print(f"❌ Failed to create database: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error creating database: {e}")
        return False

def test_connection():
    """Test connection to the new database."""
    print("\n🔍 Testing connection to 'ptolemies' database...")
    
    cmd = [
        'cypher-shell',
        '-a', 'bolt://localhost:7687',
        '-u', 'neo4j',
        '-p', 'ptolemies',
        '-d', 'ptolemies'
    ]
    
    test_query = "RETURN 'Connected to ptolemies database!' as message;"
    
    try:
        result = subprocess.run(
            cmd,
            input=test_query,
            text=True,
            capture_output=True,
            timeout=10
        )
        
        if result.returncode == 0:
            print("✅ Successfully connected to 'ptolemies' database")
            print(f"Response: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ Connection test failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Connection test error: {e}")
        return False

def main():
    """Main execution."""
    print("🚀 Setting up Ptolemies Database in Neo4j")
    print("=" * 50)
    
    # Create the database
    if create_database():
        # Test connection
        if test_connection():
            print("\n🎉 Database setup complete!")
            print("You can now run the import script:")
            print("export NEO4J_PASSWORD='ptolemies'")
            print("python3 neo4j_import_from_surrealdb.py")
        else:
            print("\n⚠️ Database created but connection test failed")
            print("Try running the import anyway - it might work")
    else:
        print("\n❌ Database creation failed")
        print("The import script will fall back to using the 'neo4j' database")

if __name__ == "__main__":
    main()