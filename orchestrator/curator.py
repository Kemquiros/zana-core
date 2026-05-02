import asyncio
import hashlib
import json
import logging
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
from orchestrator.transport import transport_from_env
from procedural_memory.manager import SkillRegistry

load_dotenv(Path(__file__).parent.parent / ".env")

logging.basicConfig(level=logging.INFO, format="🔬 [%(asctime)s] %(message)s")
logger = logging.getLogger("Curator")

_REPO_ROOT = Path(__file__).parent.parent
_TRAJECTORIES_DIR = _REPO_ROOT / "sensory" / "data" / "trajectories"
_WISDOM_INBOX_PATH = _REPO_ROOT / "sensory" / "data" / "wisdom_inbox.json"

_MINE_PROMPT = """You are analyzing ZANA session trajectories to extract reusable cognitive patterns.

Below are {count} trajectory summaries. Each contains a task, plan steps, and outcome.

Trajectories:
{trajectories}

Your job: identify patterns that appear in ≥2 trajectories and would be valuable as a reusable skill.
For each pattern found, return a JSON object in this list:

[
  {{
    "name": "Short skill name (3-5 words)",
    "domain": "one of: reasoning, code, research, writing, analysis, system, general",
    "trigger": "When should this skill activate (1 sentence)",
    "steps": ["step 1", "step 2", "step 3"],
    "confidence": 0.0-1.0
  }}
]

Return only valid JSON array. If no patterns found, return []. No explanation."""

_IMPROVE_PROMPT = """You are reviewing a ZANA cognitive skill with degraded performance.

Skill: {name}
Domain: {domain}
Current steps: {steps}
Metrics: executions={executions}, success_rate={success_rate:.0%}, q_value={q_value:.3f}

If the steps can be meaningfully improved, return JSON:
{{"improved_steps": ["step 1", "step 2", ...]}}

If the skill is fundamentally broken or redundant and should be retired, return:
{{"improved_steps": null}}

Return only valid JSON, no explanation."""


class SkillCurator:
    def __init__(
        self,
        registry: SkillRegistry,
        chronicler,
        stale_days: int = 7,
    ):
        self.registry = registry
        self.chronicler = chronicler
        self.stale_days = stale_days
        self.transport = transport_from_env("curator")

    async def review_cycle(self) -> dict:
        """Itera sobre skills stale y decide mejorar o archivar cada una."""
        stale_ids = self.registry.get_stale_skills(days_inactive=self.stale_days)
        report = {
            "timestamp": datetime.now().isoformat(),
            "reviewed": len(stale_ids),
            "improved": 0,
            "archived": 0,
            "skills": [],
        }

        for skill_id in stale_ids:
            result = await self.curate_skill(skill_id)
            action = result["action"]
            if action in ("improve", "archive"):
                report[action + "d"] += 1
            report["skills"].append(result)

        if self.chronicler and report["reviewed"] > 0:
            self.chronicler.save_curator_report(report)

        logger.info(
            f"Ciclo completado: {report['reviewed']} revisadas, "
            f"{report['improved']} mejoradas, {report['archived']} archivadas"
        )
        return report

    async def curate_skill(self, skill_id: str) -> dict:
        """Intenta mejorar una skill via LLM. Si falla, la archiva."""
        skill = self.registry.skills.get(skill_id)
        if not skill:
            return {"skill_id": skill_id, "action": "skip", "reason": "not found"}

        improved_steps = await self._ask_llm_to_improve(skill)

        if improved_steps is not None:
            skill["steps"] = improved_steps
            skill["lifecycle_state"] = "active"
            skill["q_value"] = 0.5  # Reset neutral tras mejora
            self.registry.save()
            logger.info(f"Skill '{skill_id}' mejorada y reactivada.")
            return {"skill_id": skill_id, "action": "improve", "new_steps": improved_steps}
        else:
            self.registry.archive_skill(skill_id, reason="curator: no viable improvement")
            logger.info(f"Skill '{skill_id}' archivada.")
            return {"skill_id": skill_id, "action": "archive"}

    async def _ask_llm_to_improve(self, skill: dict) -> Optional[list]:
        """Consulta Claude Haiku para mejorar los pasos de una skill degradada.
        Retorna lista de pasos mejorados, [] para mantener sin cambios, None para archivar.
        En caso de error de API, retorna [] para no archivar por fallo de red.
        """
        metrics = skill.get("metrics", {})
        executions = metrics.get("executions", 0)
        successes = metrics.get("successes", 0)
        success_rate = successes / executions if executions > 0 else 0.0

        prompt = _IMPROVE_PROMPT.format(
            name=skill.get("name", "unknown"),
            domain=skill.get("domain", "general"),
            steps=json.dumps(skill.get("steps", []), ensure_ascii=False),
            executions=executions,
            success_rate=success_rate,
            q_value=skill.get("q_value", 0.5),
        )

        try:
            text = await self.transport.ainvoke_prompt(prompt)
            data = json.loads(text)
            return data.get("improved_steps")
        except Exception as e:
            logger.warning(f"LLM call failed ({e}). Manteniendo skill activa.")
            return []  # Fallo de red/parse → conservar, no archivar


    async def mine_trajectories(
        self,
        trajectories_dir: Path = _TRAJECTORIES_DIR,
        min_trajectories: int = 5,
        min_pattern_occurrences: int = 2,
    ) -> dict:
        """Mine session trajectories for recurring patterns → propose as WisdomRules.

        Reads JSONL files from trajectories_dir, batches them, asks LLM to extract
        reusable patterns, and writes proposals to wisdom_inbox.json for user approval.
        """
        if not trajectories_dir.exists():
            return {"mined": 0, "proposed": 0}

        # Load trajectories
        entries: list[dict] = []
        for f in sorted(trajectories_dir.glob("*.jsonl")):
            try:
                for line in f.read_text().splitlines():
                    line = line.strip()
                    if line:
                        entries.append(json.loads(line))
            except Exception as e:
                logger.warning(f"Failed to read trajectory file {f}: {e}")

        if len(entries) < min_trajectories:
            logger.info(f"Only {len(entries)} trajectories — need {min_trajectories} to mine patterns.")
            return {"mined": len(entries), "proposed": 0}

        # Build summarized trajectory texts for LLM
        summaries: list[str] = []
        for e in entries[-50:]:  # last 50 trajectories, most recent patterns
            task = e.get("task", "")[:120]
            outcome = e.get("outcome", {})
            success = outcome.get("success", False) if isinstance(outcome, dict) else False
            plan = e.get("plan", [])
            steps_preview = " → ".join(str(s)[:60] for s in (plan[:3] if isinstance(plan, list) else []))
            summaries.append(f"Task: {task} | Steps: {steps_preview} | Success: {success}")

        prompt = _MINE_PROMPT.format(
            count=len(summaries),
            trajectories="\n".join(f"{i+1}. {s}" for i, s in enumerate(summaries)),
        )

        try:
            text = await self.transport.ainvoke_prompt(prompt)
            proposals_raw: list[dict] = json.loads(text)
        except Exception as e:
            logger.warning(f"Trajectory mining LLM call failed: {e}")
            return {"mined": len(entries), "proposed": 0}

        if not proposals_raw:
            return {"mined": len(entries), "proposed": 0}

        # Load existing inbox to avoid duplicates
        inbox = _load_wisdom_inbox()
        existing_names = {p["name"].lower() for p in inbox.get("pending", [])}

        added = 0
        for proposal in proposals_raw:
            name = proposal.get("name", "")
            if not name or name.lower() in existing_names:
                continue
            if proposal.get("confidence", 0) < 0.5:
                continue

            wisdom_id = hashlib.sha256(
                (name + datetime.now().isoformat()).encode()
            ).hexdigest()[:12]

            inbox.setdefault("pending", []).append({
                "id": wisdom_id,
                "name": name,
                "domain": proposal.get("domain", "general"),
                "trigger": proposal.get("trigger", ""),
                "steps": proposal.get("steps", []),
                "confidence": proposal.get("confidence", 0.5),
                "source": "trajectory_mining",
                "proposed_at": datetime.now().isoformat(),
                "status": "pending",
            })
            existing_names.add(name.lower())
            added += 1

        _save_wisdom_inbox(inbox)
        logger.info(f"Auto-WisdomRules: mined {len(entries)} trajectories → proposed {added} new rules")
        return {"mined": len(entries), "proposed": added}


def _load_wisdom_inbox() -> dict:
    if _WISDOM_INBOX_PATH.exists():
        try:
            return json.loads(_WISDOM_INBOX_PATH.read_text())
        except Exception:
            pass
    return {"pending": [], "approved": [], "rejected": []}


def _save_wisdom_inbox(inbox: dict) -> None:
    _WISDOM_INBOX_PATH.parent.mkdir(parents=True, exist_ok=True)
    _WISDOM_INBOX_PATH.write_text(json.dumps(inbox, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    async def _test():
        reg = SkillRegistry()

        reg.register_skill(
            "stale_test_skill",
            "Stale Test Skill",
            ["do a thing", "hope it works", "pray"],
            domain="test",
        )
        skill = reg.skills["stale_test_skill"]
        skill["metrics"]["executions"] = 10
        skill["metrics"]["successes"] = 2
        skill["q_value"] = 0.25
        skill["last_executed"] = (datetime.now() - timedelta(days=10)).isoformat()
        reg.save()

        curator = SkillCurator(registry=reg, chronicler=None, stale_days=7)
        print(f"Transport: {curator.transport}")
        report = await curator.review_cycle()
        print(json.dumps(report, indent=2, ensure_ascii=False))
        print("\nSummary:", reg.get_skills_summary())

    asyncio.run(_test())
