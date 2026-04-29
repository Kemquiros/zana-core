"""
Trajectory Capture — pipeline toward sovereign model fine-tuning.

Saves completed ZANA sessions in two formats:
  1. ZANA native JSONL  → data/trajectories/YYYY-MM-DD.jsonl
  2. ShareGPT JSONL     → data/trajectories/sharegpt/YYYY-MM-DD.jsonl

ShareGPT format is compatible with LLaMA Factory, Axolotl, and most
fine-tuning frameworks — enabling training a sovereign ZANA model on
real interaction data.
"""
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from langchain_core.messages import BaseMessage

logger = logging.getLogger(__name__)

ZANA_VERSION = "2.9.6"
_DATA_ROOT = Path(__file__).parent.parent / "data" / "trajectories"


class TrajectoryCapture:
    def __init__(self, data_root: Path = _DATA_ROOT):
        self.native_dir = data_root
        self.sharegpt_dir = data_root / "sharegpt"
        self.native_dir.mkdir(parents=True, exist_ok=True)
        self.sharegpt_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def capture(self, state: Dict[str, Any]) -> str:
        """Capture a completed session. Returns the trajectory ID."""
        session_id = str(uuid.uuid4())
        today = datetime.now().strftime("%Y-%m-%d")

        native = self._to_native(state, session_id)
        sharegpt = self._to_sharegpt(state, session_id)

        self._append_jsonl(self.native_dir / f"{today}.jsonl", native)
        self._append_jsonl(self.sharegpt_dir / f"{today}.jsonl", sharegpt)

        logger.info(
            f"Trajectory {session_id[:8]} captured — "
            f"{len(state.get('messages', []))} messages, "
            f"{state.get('iterations', 0)} iterations, "
            f"{state.get('compression_count', 0)} compressions."
        )
        return session_id

    # ------------------------------------------------------------------
    # Format converters
    # ------------------------------------------------------------------

    def _to_native(self, state: Dict[str, Any], session_id: str) -> dict:
        messages = state.get("messages", [])
        return {
            "id": session_id,
            "timestamp": datetime.now().isoformat(),
            "task": state.get("task", self._extract_task(messages)),
            "plan": state.get("plan", []),
            "observations": state.get("observations", []),
            "iterations": state.get("iterations", 0),
            "compression_count": state.get("compression_count", 0),
            "messages": self._serialize_messages(messages),
            "outcome": "success" if state.get("task_completed") else "partial",
            "metadata": {
                "zana_version": ZANA_VERSION,
            },
        }

    def _to_sharegpt(self, state: Dict[str, Any], session_id: str) -> dict:
        """ShareGPT format: conversations list with from/value pairs."""
        messages = state.get("messages", [])
        conversations: List[dict] = []

        # System preamble: plan + task as context
        task = state.get("task", self._extract_task(messages))
        plan = state.get("plan", [])
        if plan:
            system_content = f"Task: {task}\nPlan:\n" + "\n".join(plan)
            conversations.append({"from": "system", "value": system_content})

        # Convert messages to ShareGPT turns
        for msg in messages:
            role, content = self._classify_message(msg)
            if not content.strip():
                continue
            # Merge consecutive same-role turns
            if conversations and conversations[-1]["from"] == role:
                conversations[-1]["value"] += f"\n{content}"
            else:
                conversations.append({"from": role, "value": content})

        # Append observations as final assistant reflection
        observations = state.get("observations", [])
        if observations:
            obs_text = "Observations:\n" + "\n".join(f"- {o}" for o in observations)
            if conversations and conversations[-1]["from"] == "gpt":
                conversations[-1]["value"] += f"\n\n{obs_text}"
            else:
                conversations.append({"from": "gpt", "value": obs_text})

        return {
            "id": session_id,
            "conversations": conversations,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _classify_message(self, msg: BaseMessage) -> tuple[str, str]:
        content = str(msg.content)
        msg_type = getattr(msg, "type", "")
        if msg_type == "human":
            return "human", content
        if content.startswith("[CONTEXT SUMMARY"):
            return "system", content
        return "gpt", content

    def _serialize_messages(self, messages: List[BaseMessage]) -> List[dict]:
        return [
            {"role": role, "content": content}
            for role, content in (self._classify_message(m) for m in messages)
        ]

    def _extract_task(self, messages: List[BaseMessage]) -> str:
        for msg in messages:
            if getattr(msg, "type", "") == "human":
                return str(msg.content)
        return messages[0].content if messages else "unknown"

    @staticmethod
    def _append_jsonl(path: Path, record: dict):
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    import tempfile
    from langchain_core.messages import HumanMessage, AIMessage

    with tempfile.TemporaryDirectory() as tmp:
        cap = TrajectoryCapture(data_root=Path(tmp))

        state = {
            "task": "Deploy VECANOVA landing page",
            "messages": [
                HumanMessage(content="Deploy VECANOVA landing page"),
                AIMessage(content="Initiating deployment sequence."),
                HumanMessage(content="Check status please."),
                AIMessage(content="Build complete. Live at vecanova.com."),
            ],
            "plan": ["1. Build", "2. Deploy", "3. Verify"],
            "observations": ["Build took 42s", "DNS propagated in <1min"],
            "iterations": 3,
            "compression_count": 0,
            "task_completed": True,
        }

        session_id = cap.capture(state)
        print(f"Session ID: {session_id}")

        native_file = list(Path(tmp).glob("*.jsonl"))[0]
        native = json.loads(native_file.read_text().strip())
        print(f"\nNative format keys: {list(native.keys())}")
        print(f"Outcome: {native['outcome']}")

        sharegpt_file = list((Path(tmp) / "sharegpt").glob("*.jsonl"))[0]
        sg = json.loads(sharegpt_file.read_text().strip())
        print(f"\nShareGPT turns: {len(sg['conversations'])}")
        for turn in sg["conversations"]:
            print(f"  [{turn['from']}] {turn['value'][:60]}")

        print("\nTrajectory Capture: OK")
