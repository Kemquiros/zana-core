import asyncio
import json
import logging
import os
import sys
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
