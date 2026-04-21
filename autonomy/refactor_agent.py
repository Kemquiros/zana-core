import sys
import os
from pathlib import Path
from typing import Dict, Any

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))
from router.zana_router import route

class RefactorAgent:
    """
    ZANA Refactor Agent (Phase 8).
    Translates Python modules to Rust using Claude Opus for high-fidelity porting.
    """
    def __init__(self):
        self.output_dir = Path(__file__).parent.parent / "rust_core/src"

    def refactor_to_rust(self, python_file_path: str):
        file_path = Path(python_file_path)
        if not file_path.exists():
            print(f"❌ Error: File {python_file_path} not found.")
            return

        print(f"--- 🛠️ REFACTORING: {file_path.name} to RUST ---")
        code = file_path.read_text()

        prompt = f"""
        You are a ZANA Senior Systems Engineer. 
        Your task is to translate this Python module into idiomatic, high-performance RUST code.
        
        CRITERIA:
        1. Use f64 for calculations.
        2. Implement it as a public struct/module.
        3. Include doc comments explaining the logic.
        4. No external dependencies if possible (use std).
        
        PYTHON CODE:
        ```python
        {code}
        ```
        
        Reply ONLY with the valid RUST code.
        """

        # Force Opus for the translation
        print("Deploying Claude Opus for translation...")
        res = route(prompt, force_backend="claude", force_model="opus", use_pi=True)
        
        rust_code = res.get("result", "")
        if "[ERROR]" in rust_code:
            print(f"❌ Translation failed: {rust_code}")
            return

        output_file = self.output_dir / f"{file_path.stem}.rs"
        output_file.write_text(rust_code)
        print(f"✅ RUST CORE FORGED: {output_file}")

if __name__ == "__main__":
    agent = RefactorAgent()
    # Mock call - in production this would take the file as argument
    # agent.refactor_to_rust("../episodic/kalman.py")
