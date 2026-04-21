import json
import sys
from pathlib import Path

# Fix python path since this is a one-off script
sys.path.append(str(Path(__file__).parent))
from server import semantic_search, get_entity, related_concepts

query = sys.argv[1]
action = sys.argv[2] if len(sys.argv) > 2 else "search"

print(f"--- Action: {action} | Query: {query} ---")
if action == "search":
    print(semantic_search(query))
elif action == "entity":
    print(get_entity(query))
elif action == "related":
    print(related_concepts(query))
