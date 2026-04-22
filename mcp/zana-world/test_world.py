import sys
from pathlib import Path

# Fix python path
sys.path.append(str(Path(__file__).parent))
from server import query_world_model, simulate_impact

action = sys.argv[1] if len(sys.argv) > 1 else "simulate"
target = sys.argv[2] if len(sys.argv) > 2 else "zana_core"

if action == "simulate":
    print(simulate_impact(target))
elif action == "query":
    print(query_world_model(f"MATCH (n) WHERE n.id = '{target}' RETURN n"))
