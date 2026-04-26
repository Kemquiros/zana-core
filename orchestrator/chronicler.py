import os
import json
import logging
from datetime import datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="🖋️ [%(asctime)s] %(message)s")
logger = logging.getLogger("Chronicler")

class TheChronicler:
    def __init__(self, wiki_path: str = "claude-obsidian/wiki"):
        self.wiki_path = Path(wiki_path)
        self.diaries_path = self.wiki_path / "diaries"
        self.skills_path = self.wiki_path / "skills"
        
        # Asegurar directorios
        self.diaries_path.mkdir(parents=True, exist_ok=True)
        self.skills_path.mkdir(parents=True, exist_ok=True)

    def save_diary_entry(self, session_trace: list):
        """Guardar entrada episódica en el diario de Obsidian."""
        today = datetime.now().strftime("%Y-%m-%d")
        file_path = self.diaries_path / f"{today}.md"
        
        content = f"# Aeon Diary: {today}\n\n## Session Traces\n"
        for trace in session_trace:
            content += f"- {trace}\n"
        
        with open(file_path, "a") as f:
            f.write(content + "\n")
        logger.info(f"Entrada de diario guardada en {file_path}")

    def update_semantic_memory(self, concepts: list):
        """Actualizar Wiki con nuevos conceptos aprendidos."""
        # En una implementación real, esto crearía o actualizaría archivos .md en la wiki
        logger.info(f"Actualizando memoria semántica con: {concepts}")

    def extract_procedural_skill(self, task_name: str, workflow: list):
        """Si un flujo fue exitoso, guardarlo como una nueva habilidad."""
        skill_file = self.skills_path / f"{task_name.lower().replace(' ', '_')}.json"
        skill_data = {
            "name": task_name,
            "workflow": workflow,
            "created_at": datetime.now().isoformat()
        }
        with open(skill_file, "w") as f:
            json.dump(skill_data, f, indent=2)
        logger.info(f"Nueva habilidad guardada: {skill_file}")

if __name__ == "__main__":
    chronicler = TheChronicler()
    chronicler.save_diary_entry(["Iniciada integración de KoruOS", "Refactorizado orquestador a ReAct"])
    chronicler.extract_procedural_skill("Deploy Koru Body", ["setup_monorepo", "build_proto", "start_server"])
