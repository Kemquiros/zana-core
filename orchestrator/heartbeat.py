import asyncio
import json
import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

import httpx
from plyer import notification

sys.path.insert(0, str(Path(__file__).parent.parent))
from orchestrator.chronicler import TheChronicler
from orchestrator.curator import SkillCurator
from procedural_memory.manager import SkillRegistry

# Configuración de logs
logging.basicConfig(level=logging.INFO, format="💓 [%(asctime)s] %(message)s")
logger = logging.getLogger("Heartbeat")

RELEASES_API = "https://api.github.com/repos/kemquiros/zana-core/releases/latest"
UPDATE_STATE_FILE = Path.home() / ".config" / "zana" / "update_state.json"

class AeonHeartbeat:
    def __init__(self, interval_minutes: int = 30):
        self.interval = interval_minutes * 60
        self.is_running = False
        self._chronicler = TheChronicler()
        self._curator = SkillCurator(
            registry=SkillRegistry(),
            chronicler=self._chronicler,
            stale_days=7,
        )
        self._last_update_check = 0

    def _parse_changelog(self, body: str) -> Dict[str, List[str]]:
        """Parse GitHub release body into modular sections."""
        sections = {
            "Core": [],
            "Memory": [],
            "Senses": [],
            "UI": [],
            "Other": []
        }
        
        current_section = "Other"
        lines = body.split("\n")
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Match headers like [Core], [Memory], etc.
            match = re.search(r"\[(Core|Memory|Senses|UI)\]", line, re.IGNORECASE)
            if match:
                current_section = match.group(1).capitalize()
                continue
            
            if line.startswith(("-", "*", "•")):
                clean_line = line.lstrip("-*• ").strip()
                if clean_line:
                    sections[current_section].append(clean_line)
        
        return {k: v for k, v in sections.items() if v}

    async def _check_for_updates(self):
        """Check GitHub for new ZANA releases and notify the user."""
        now = datetime.now().timestamp()
        # Check every 6 hours (21600 seconds)
        if now - self._last_update_check < 21600:
            return

        logger.info("Verificando evolución en el Gran Enjambre (GitHub)...")
        self._last_update_check = now
        
        try:
            from importlib.metadata import version as pkg_version
            current_v = pkg_version("zana")
        except Exception:
            current_v = "0.0.0"

        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(RELEASES_API, timeout=10)
                r.raise_for_status()
                data = r.json()
                latest_v = data.get("tag_name", "").lstrip("v")
                
                if latest_v and latest_v != current_v:
                    logger.info(f"¡Nueva evolución detectada! v{current_v} -> v{latest_v}")
                    
                    # Check if we already notified for this version
                    staged_data = {}
                    if UPDATE_STATE_FILE.exists():
                        try:
                            staged_data = json.loads(UPDATE_STATE_FILE.read_text())
                        except Exception:
                            pass
                    
                    if staged_data.get("latest_version") == latest_v and staged_data.get("status") == "NOTIFIED":
                        return

                    # Prepare staged data
                    changelog = self._parse_changelog(data.get("body", ""))
                    staged_data = {
                        "latest_version": latest_v,
                        "current_version": current_v,
                        "status": "NOTIFIED",
                        "timestamp": datetime.now().isoformat(),
                        "changelog": changelog
                    }
                    
                    UPDATE_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
                    UPDATE_STATE_FILE.write_text(json.dumps(staged_data, indent=2))
                    
                    # Notify user
                    notification.notify(
                        title="ZANA: Evolución Detectada",
                        message=f"Una nueva versión (v{latest_v}) está lista. Abre Aria UI para supervisar la ascensión.",
                        app_name="ZANA",
                        timeout=10
                    )
        except Exception as e:
            logger.error(f"Error al verificar actualizaciones: {e}")

    async def scan_environment(self) -> List[str]:
        """Escanear servidores MCP, Shadow Observer y Wiki por nuevas tareas."""
        logger.info("Escaneando entorno (Shadow, Wiki, MCP)...")
        alerts = []
        
        # Consultar Shadow Observer por patrones de usuario recientes
        try:
            import requests
            # response = requests.get("http://localhost:54444/mcp/context")
            # user_activity = response.json()
            # if user_activity.get("alignment") < 40:
            #    alerts.append("Low resonance detected. Initiating alignment ritual.")
        except Exception:
            pass
            
        return alerts

    async def audit_internal_state(self) -> Dict:
        """Consultar el Reasoning Engine en Rust para salud del sistema."""
        logger.info("Auditoría de estado interno (Survival Rules)...")
        # Simulación de estado
        return {"status": "SOVEREIGN", "liquidity": "STABLE", "health": 1.0}

    async def propose_actions(self, context: Dict) -> List[str]:
        """Generar propuestas proactivas (ToT / Brainstorming)."""
        logger.info("Generando propuestas proactivas...")
        return ["Revisar logs de KoruOS", "Optimizar memoria episódica"]

    async def pulse(self):
        """Un único 'latido' de ZANA."""
        logger.info("--- INICIANDO LATIDO DE AEÓN ---")

        # 0. Evolución (Sovereign Update Pulse)
        await self._check_for_updates()

        # 1. Sentir
        alerts = await self.scan_environment()
        state = await self.audit_internal_state()

        # 2. Pensar / Proponer
        proposals = await self.propose_actions(state)

        # 3. Curar memoria procedural (Curator cycle)
        curator_report = await self._curator.review_cycle()
        if curator_report["reviewed"] > 0:
            logger.info(
                f"Curator: {curator_report['reviewed']} revisadas | "
                f"{curator_report['improved']} mejoradas | "
                f"{curator_report['archived']} archivadas"
            )

        # 4. Actuar (Trigger Orchestrator if necessary)
        if proposals or alerts:
            logger.info(f"Propuestas generadas: {proposals}")
            # Aquí se invocaría graph.run_task(proposals[0])

        logger.info("--- LATIDO COMPLETADO ---")

    async def start(self):
        self.is_running = True
        logger.info(f"Servicio de Latido iniciado. Intervalo: {self.interval/60} min.")
        while self.is_running:
            await self.pulse()
            await asyncio.sleep(self.interval)

if __name__ == "__main__":
    heartbeat = AeonHeartbeat(interval_minutes=5)
    try:
        asyncio.run(heartbeat.start())
    except KeyboardInterrupt:
        logger.info("Latido detenido por el usuario.")
