import ast
import re
import time
from pathlib import Path
from typing import Any


class MapBridge:
    """
    Translates Obsidian Vault metadata into parameters for the Dejavu map generator.
    """

    def __init__(self, vault_path: str):
        self.vault_path = Path(vault_path)

    def generate_params(self) -> dict[str, Any]:
        """
        Scans the vault and aggregates signals into map parameters.
        """
        files = list(self.vault_path.glob("**/*.md"))

        entropy_score = 0
        total_age_factor = 0
        tag_counts = {}
        clusters = {}

        now = time.time()

        for md_file in files:
            content = md_file.read_text(errors="ignore")

            # 1. Entropy: Detect syntax errors in Python blocks
            python_blocks = re.findall(r"```python\n(.*?)\n```", content, re.DOTALL)
            for block in python_blocks:
                try:
                    ast.parse(block)
                except SyntaxError:
                    entropy_score += 1

            # 2. Memory Fog: Calculate age factor
            mtime = md_file.stat().st_mtime
            age_days = (now - mtime) / (24 * 3600)
            if age_days > 30:
                total_age_factor += (age_days - 30) / 100

            # 3. Biomes & Clusters: Parse tags and parent directories
            tags = re.findall(r"#(\w+)", content)
            for tag in tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

            # Use parent directory as cluster signal
            parent_name = md_file.parent.name
            if parent_name != self.vault_path.name:
                clusters[parent_name] = clusters.get(parent_name, 0) + 1

        return {
            "gaussian_centers": list(clusters.keys()),
            "entropy_level": min(1.0, entropy_score / 10.0),
            "memory_fog": min(1.0, total_age_factor / 5.0),
            "biome_weights": tag_counts,
            "file_count": len(files),
        }
