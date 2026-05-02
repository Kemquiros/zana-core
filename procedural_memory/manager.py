import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional


class SkillRegistry:
    """
    Manages the Procedural Memory (Skills) of ZANA.
    Stores recipes, execution metrics, and Q-values for optimal routing.
    """

    def __init__(self, storage_path: str = "skills_registry.json"):
        self.storage_path = Path(__file__).parent / storage_path
        self.skills = self._load()

    def _load(self) -> Dict[str, Any]:
        if self.storage_path.exists():
            return json.loads(self.storage_path.read_text())
        return {}

    def save(self):
        self.storage_path.write_text(json.dumps(self.skills, indent=2))

    def register_skill(
        self, skill_id: str, name: str, steps: List[str], domain: str = "general"
    ):
        if skill_id not in self.skills:
            self.skills[skill_id] = {
                "name": name,
                "domain": domain,
                "steps": steps,
                "metrics": {
                    "executions": 0,
                    "successes": 0,
                    "avg_score": 0.0,
                    "last_outcome": None,
                },
                "q_value": 0.5,  # Initial neutrality
                "version": "1.0.0",
                "created_at": datetime.now().isoformat(),
                "last_executed": None,
                "lifecycle_state": "active",
            }
            self.save()

    def update_skill_performance(self, skill_id: str, success: bool, score: float):
        """
        Offline RL Lite: Update Q-value based on outcome.
        Q(s,a) = Q(s,a) + alpha * (Reward - Q(s,a))
        """
        if skill_id not in self.skills:
            return

        skill = self.skills[skill_id]
        metrics = skill["metrics"]

        # 1. Update basic metrics
        metrics["executions"] += 1
        if success:
            metrics["successes"] += 1

        # Incremental average
        metrics["avg_score"] = (
            metrics["avg_score"] * (metrics["executions"] - 1) + score
        ) / metrics["executions"]

        # 2. Update Q-Value (alpha = 0.1, reward = score)
        alpha = 0.1
        reward = score if success else -1.0  # Penalty for failure
        skill["q_value"] += alpha * (reward - skill["q_value"])

        # 3. Handle degradation (Self-Healing trigger)
        success_rate = metrics["successes"] / metrics["executions"]
        if metrics["executions"] > 5 and success_rate < 0.6:
            skill["status"] = "NEEDS_REFACTOR"

        self.save()

    def get_best_skill(self, domain: str) -> Optional[str]:
        """Returns the skill_id with highest Q-value in a given domain."""
        domain_skills = [
            s_id for s_id, s in self.skills.items()
            if s["domain"] == domain and s.get("lifecycle_state", "active") == "active"
        ]
        if not domain_skills:
            return None
        return max(domain_skills, key=lambda s_id: self.skills[s_id]["q_value"])

    def mark_executed(self, skill_id: str):
        """Actualiza last_executed al momento actual."""
        if skill_id in self.skills:
            self.skills[skill_id]["last_executed"] = datetime.now().isoformat()
            self.save()

    def get_stale_skills(self, days_inactive: int = 7, q_threshold: float = 0.5) -> List[str]:
        """Retorna skill_ids activos que están degradados por inactividad o bajo rendimiento."""
        stale = []
        cutoff = datetime.now() - timedelta(days=days_inactive)
        for skill_id, skill in self.skills.items():
            if skill.get("lifecycle_state", "active") != "active":
                continue
            metrics = skill.get("metrics", {})
            executions = metrics.get("executions", 0)
            successes = metrics.get("successes", 0)
            q_value = skill.get("q_value", 0.5)
            last_executed = skill.get("last_executed")
            # Stale por inactividad + Q bajo
            if last_executed:
                last_dt = datetime.fromisoformat(last_executed)
                if last_dt < cutoff and q_value < q_threshold:
                    stale.append(skill_id)
                    continue
            # Stale por tasa de éxito crítica
            if executions > 5 and successes / executions < 0.4:
                stale.append(skill_id)
        return stale

    def archive_skill(self, skill_id: str, reason: str = "curator"):
        """Mueve una skill a estado archived. Nunca la elimina."""
        if skill_id in self.skills:
            self.skills[skill_id]["lifecycle_state"] = "archived"
            self.skills[skill_id]["archived_at"] = datetime.now().isoformat()
            self.skills[skill_id]["archive_reason"] = reason
            self.save()

    def get_skills_summary(self) -> Dict[str, int]:
        """Retorna conteo de skills por lifecycle_state."""
        summary: Dict[str, int] = {}
        for skill in self.skills.values():
            state = skill.get("lifecycle_state", "active")
            summary[state] = summary.get(state, 0) + 1
        return summary


    # ── Z-Skill v1.0: SKILL.md I/O ────────────────────────────────────────────

    def load_skill_from_skillmd(self, path: Path) -> Optional[str]:
        """Parse a SKILL.md file (agentskills.io compatible + ZANA extensions).

        Expected frontmatter fields:
          name, version, domain, author, license, trigger (ZANA extension),
          pillar, wisdom_level, q_value_hint, civic_hash (ZANA extensions)

        Steps parsed from the ## Steps section (numbered list items).
        Returns skill_id if successfully registered, None on parse failure.
        """
        try:
            content = path.read_text()
        except Exception:
            return None

        # Parse YAML frontmatter between --- delimiters
        fm: dict = {}
        body = content
        fm_match = re.match(r"^---\n(.*?)\n---\n(.*)", content, re.DOTALL)
        if fm_match:
            fm_text, body = fm_match.group(1), fm_match.group(2)
            for line in fm_text.splitlines():
                if ":" in line:
                    key, _, val = line.partition(":")
                    fm[key.strip()] = val.strip().strip('"').strip("'")

        name = fm.get("name") or path.stem
        domain = fm.get("domain", "general")
        version = fm.get("version", "1.0.0")

        # Parse steps from ## Steps section
        steps: list[str] = []
        steps_match = re.search(r"##\s+Steps\s*\n(.*?)(?:\n##|\Z)", body, re.DOTALL)
        if steps_match:
            for line in steps_match.group(1).splitlines():
                line = line.strip()
                # Accept numbered list (1. step), bullet (- step), or plain text
                step_text = re.sub(r"^(\d+\.\s*|-\s*|\*\s*)", "", line).strip()
                if step_text:
                    steps.append(step_text)

        if not steps:
            return None

        # Derive skill_id from name
        skill_id = re.sub(r"[^a-z0-9_]", "_", name.lower()).strip("_")

        self.register_skill(skill_id=skill_id, name=name, steps=steps, domain=domain)

        # Apply ZANA-specific extensions
        if skill_id in self.skills:
            skill = self.skills[skill_id]
            skill["version"] = version
            if "author" in fm:
                skill["author"] = fm["author"]
            if "license" in fm:
                skill["license"] = fm["license"]
            if "trigger" in fm:
                skill["trigger"] = fm["trigger"]
            if "pillar" in fm:
                skill["pillar"] = fm["pillar"]
            if "wisdom_level" in fm:
                skill["wisdom_level"] = fm["wisdom_level"]
            if "q_value_hint" in fm:
                try:
                    skill["q_value"] = float(fm["q_value_hint"])
                except ValueError:
                    pass
            if "civic_hash" in fm:
                skill["civic_hash"] = fm["civic_hash"]
            skill["source"] = "skillmd_import"
            self.save()

        return skill_id

    def export_skill_to_skillmd(self, skill_id: str, output_path: Path) -> bool:
        """Export a skill to SKILL.md format (agentskills.io + ZANA extensions).

        Returns True on success.
        """
        skill = self.skills.get(skill_id)
        if not skill:
            return False

        name = skill.get("name", skill_id)
        domain = skill.get("domain", "general")
        version = skill.get("version", "1.0.0")
        author = skill.get("author", "ZANA")
        license_ = skill.get("license", "MIT")
        trigger = skill.get("trigger", "")
        pillar = skill.get("pillar", "Operator")
        wisdom_level = skill.get("wisdom_level", "Warrior")
        q_value = skill.get("q_value", 0.5)
        steps = skill.get("steps", [])

        metrics = skill.get("metrics", {})
        executions = metrics.get("executions", 0)
        successes = metrics.get("successes", 0)
        success_rate = successes / executions if executions > 0 else 0.0

        numbered_steps = "\n".join(f"{i+1}. {s}" for i, s in enumerate(steps))

        content = f"""---
name: {name}
version: {version}
domain: {domain}
author: {author}
license: {license_}
trigger: "{trigger}"
pillar: {pillar}
wisdom_level: {wisdom_level}
q_value_hint: {q_value:.3f}
---

# {name}

> {trigger or f"A {domain} skill for ZANA Aeons."}

## Steps

{numbered_steps}

## Metrics

| Field | Value |
|---|---|
| Executions | {executions} |
| Success Rate | {success_rate:.0%} |
| Q-Value | {q_value:.3f} |
| Lifecycle | {skill.get("lifecycle_state", "active")} |

---
*Generated by ZANA v3.0 — Z-Skill v1.0 format*
"""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content)
        return True


if __name__ == "__main__":
    print("--- 🧠 PROCEDURAL MEMORY TEST ---")
    reg = SkillRegistry()

    # Register a mock skill
    reg.register_skill(
        "deploy_app", "FastAPI Deployment", ["build", "test", "deploy"], domain="devops"
    )

    # Simulate some runs
    reg.update_skill_performance("deploy_app", True, 0.9)
    reg.update_skill_performance("deploy_app", False, -0.5)

    best = reg.get_best_skill("devops")
    print(f"Best DevOps skill: {best} (Q={reg.skills[best]['q_value']:.4f})")
