#!/bin/bash
# View data in the Ptolemies Knowledge Base

# Base directory
PTOLEMIES_DIR="/Users/dionedge/devqai/ptolemies"

# Activate virtual environment
source "$PTOLEMIES_DIR/venv/bin/activate"

# Run the query
echo "Viewing data in the Ptolemies Knowledge Base..."
python -c "
import asyncio
from surrealdb import Surreal

async def main():
    # Connect to SurrealDB
    db = Surreal('http://localhost:8000')
    await db.connect()
    await db.signin({'user': 'root', 'pass': 'root'})
    await db.use('ptolemies', 'knowledge')
    
    # Query webpages
    result = await db.query('SELECT * FROM webpage;')
    
    if result and len(result) > 0 and result[0]:
        webpages = result[0]
        print(f'Found {len(webpages)} webpages:')
        print('---------------------------------------------------')
        for i, page in enumerate(webpages, 1):
            print(f\"{i}. ID: {page.get('id', 'No ID')}\\n   Title: {page.get('title', 'Untitled')}\\n   Source: {page.get('source', 'No source')}\\n\")
    else:
        print('No webpages found in the database')

asyncio.run(main())
"

echo "Query completed!"