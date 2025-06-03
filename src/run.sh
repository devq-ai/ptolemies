#!/bin/bash
# Run the DB client to store URLs in SurrealDB

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the DB client
python db_client.py

# Deactivate virtual environment
deactivate