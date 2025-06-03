#!/bin/bash
# Ptolemies Knowledge Base Crawler

# Define color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}===== Ptolemies Knowledge Base Crawler =====${NC}"
echo ""

# Base directory
PTOLEMIES_DIR="/Users/dionedge/devqai/ptolemies"

# Check for required files
if [ ! -f "$PTOLEMIES_DIR/data/crawl_targets.json" ]; then
  echo -e "${RED}Error: crawl_targets.json file not found!${NC}"
  echo "Please ensure the crawl targets file is properly configured."
  exit 1
fi

# Activate virtual environment
if [ -d "$PTOLEMIES_DIR/venv" ]; then
  source "$PTOLEMIES_DIR/venv/bin/activate"
else
  echo -e "${RED}Error: Virtual environment not found!${NC}"
  echo "Please create a virtual environment with required dependencies."
  exit 1
fi

# Show menu of available operations
show_menu() {
  echo -e "${BLUE}Available operations:${NC}"
  echo "1. List crawl targets"
  echo "2. Crawl specific URL"
  echo "3. Crawl all targets"
  echo "4. View stored webpages"
  echo "5. Exit"
  echo ""
  echo -e "${YELLOW}Enter your choice (1-5):${NC} "
  read choice
  
  case $choice in
    1)
      list_targets
      ;;
    2)
      crawl_url
      ;;
    3)
      crawl_all_targets
      ;;
    4)
      view_webpages
      ;;
    5)
      echo "Exiting..."
      exit 0
      ;;
    *)
      echo -e "${RED}Invalid choice!${NC}"
      show_menu
      ;;
  esac
}

# List all crawl targets
list_targets() {
  echo -e "${BLUE}Listing crawl targets...${NC}"
  echo ""
  
  cat "$PTOLEMIES_DIR/data/crawl_targets.json" | python -c "
import json, sys
data = json.load(sys.stdin)
print(f\"Found {len(data['targets'])} targets:\")
for i, target in enumerate(data['targets'], 1):
    print(f\"{i}. {target.get('name', 'Unnamed')} ({target['url']}) - {target.get('category', 'Uncategorized')} (depth: {target.get('depth', 2)})\")"
  
  echo ""
  echo -e "${GREEN}Press Enter to continue...${NC}"
  read
  show_menu
}

# Crawl a specific URL
crawl_url() {
  echo -e "${BLUE}Crawl a specific URL${NC}"
  echo -e "${YELLOW}Enter URL:${NC} "
  read url
  
  echo -e "${YELLOW}Enter name (optional):${NC} "
  read name
  
  echo -e "${YELLOW}Enter tags (comma-separated):${NC} "
  read tags_input
  tags=$(echo $tags_input | tr ',' ' ')
  
  echo -e "${YELLOW}Enter category (optional):${NC} "
  read category
  
  echo -e "${BLUE}Starting crawl of $url...${NC}"
  
  command="python $PTOLEMIES_DIR/crawl-minimal.py $url"
  if [ -n "$name" ]; then
    command="$command --name \"$name\""
  fi
  if [ -n "$tags" ]; then
    command="$command --tags $tags"
  fi
  if [ -n "$category" ]; then
    command="$command --category \"$category\""
  fi
  
  eval $command
  
  echo ""
  echo -e "${GREEN}Press Enter to continue...${NC}"
  read
  show_menu
}

# Crawl all targets
crawl_all_targets() {
  echo -e "${BLUE}Crawling all targets from crawl_targets.json...${NC}"
  echo -e "${YELLOW}This may take a while. Continue? (y/n)${NC} "
  read confirm
  
  if [ "$confirm" != "y" ]; then
    show_menu
    return
  fi
  
  python "$PTOLEMIES_DIR/crawl-targets.py"
  
  echo ""
  echo -e "${GREEN}Press Enter to continue...${NC}"
  read
  show_menu
}

# View stored webpages
view_webpages() {
  echo -e "${BLUE}Stored webpages in the knowledge base:${NC}"
  
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
    result = await db.query('SELECT id, title, source, category, tags FROM webpage;')
    
    if result and len(result) > 0 and result[0]:
        webpages = result[0]
        print(f'Found {len(webpages)} webpages:')
        print('---------------------------------------------------')
        for i, page in enumerate(webpages, 1):
            tags = ', '.join(page.get('tags', [])) if page.get('tags') else 'None'
            print(f\"{i}. {page.get('title', 'Untitled')} ({page.get('source', 'No source')})\\n   Category: {page.get('category', 'Uncategorized')}\\n   Tags: {tags}\\n   ID: {page.get('id', 'No ID')}\\n\")
    else:
        print('No webpages found in the database')

asyncio.run(main())
"
  
  echo ""
  echo -e "${GREEN}Press Enter to continue...${NC}"
  read
  show_menu
}

# Main program
show_menu