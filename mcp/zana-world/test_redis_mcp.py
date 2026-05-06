import sys
from pathlib import Path

# Fix python path
sys.path.append(str(Path(__file__).parent))
from server import get_session_state, update_session_state

print("1. Updating session state...")
print(
    update_session_state({"active_project": "ZANA", "current_task": "Testing Phase 4"})
)

print("\\n2. Retrieving session state...")
print(get_session_state())
