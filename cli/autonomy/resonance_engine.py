import json
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
from autonomy.genome import KORU_GENOME_V4


class ResonanceEngine:
    """
    ZANA Resonance Engine — Transmutes user ritual answers into cognitive archetypes.
    This module bridges the human psyche with the Aeon's behavioral parameters,
    Aeon fleet configuration, and Agora module alignment.
    """

    def __init__(self, resonance_path: str = "data/resonance_profile.json"):
        self.resonance_path = Path(resonance_path)
        self.resonance_path.parent.mkdir(parents=True, exist_ok=True)

    def process_ritual(self, answers: Dict[str, Any], user_name: str = None, user_visual_genes: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Processes the 20 questions of the Resonance Ritual to forge the Aeon's identity.
        Determines the archetype, visual genes, and initial Agora module recommendations.
        """
        # Baseline traits (0.0 to 1.0)
        # Mapping to KoruOS categories:
        # Soberanía Cognitiva, Resiliencia Emocional, Conexión Social, Propósito y Legado, Autoconocimiento
        scores = {
            "cognitive_sovereignty": 0.5,
            "emotional_resilience": 0.5,
            "social_connection": 0.5,
            "purpose_legacy": 0.5,
            "self_knowledge": 0.5,
        }

        # Weight mapping logic inspired by KoruOS synthesis.service.ts
        category_weights = {
            "Eneatipo_": "emotional_resilience",
            "Esquema_": "emotional_resilience",
            "BigFive_Neuroticism": "emotional_resilience",
            "Apego_": "social_connection",
            "Dinamica_Espiral": "social_connection",
            "BigFive_Amabilidad": "social_connection",
            "Kegan_": "social_connection",
            "Valor_Conformidad": "purpose_legacy",
            "Valor_Benevolencia": "social_connection",
            "Valor_Poder": "purpose_legacy",
            "Valor_Autodireccion": "purpose_legacy",
            "Valor_Universalismo": "cognitive_sovereignty",
            "Valor_Hedonismo": "emotional_resilience",
            "Cognicion_Ti": "cognitive_sovereignty",
            "Cognicion_Te": "cognitive_sovereignty",
            "Cognicion_Ni": "cognitive_sovereignty",
            "Cognicion_Ne": "cognitive_sovereignty",
            "Cognicion_Si": "self_knowledge",
            "Cognicion_Se": "self_knowledge",
            "ACTIVIDAD_FLOW": "self_knowledge",
            "OBJETIVO_PRIMARIO": "purpose_legacy",
            "FORTALEZA_PRIMARIA": "self_knowledge",
            "LEGADO_PRELIMINAR": "purpose_legacy",
        }

        # Iterate through phases and questions from genome
        for phase in KORU_GENOME_V4["fases"]:
            for q in phase["preguntas"]:
                ans_val = answers.get(q["id"])
                if not ans_val:
                    continue

                if q["tipo"] == "opcion_unica_categorizada":
                    # Find selected option to get its categories
                    selected_opt = next((o for o in q.get("opciones", []) if o["valor"] == ans_val), None)
                    if selected_opt:
                        for cat in selected_opt["categoria"]:
                            for prefix, score_key in category_weights.items():
                                if cat.startswith(prefix):
                                    scores[score_key] += 0.05
                                    break
                elif q["tipo"] == "abierta_critica":
                    # Open questions boost self_knowledge or specified mappings
                    score_key = "self_knowledge"
                    if q["id"] == "q8_critica": score_key = "purpose_legacy"
                    if q["id"] == "q20_critica": score_key = "purpose_legacy"
                    scores[score_key] += 0.1

        # Normalize traits to [0, 1]
        for key in scores:
            scores[key] = max(0.0, min(1.0, scores[key]))

        # --- ARCHETYPE DETERMINATION ---
        archetype = "Digital Symbiont"
        # Default genes
        visual_genes = {
            "color_palette": ["#4F46E5", "#7C3AED"],
            "pulse_speed": "dynamic",
            "particle_shape": "fluid",
        }
        
        # Merge with user provided genes if available
        if user_visual_genes:
            visual_genes.update(user_visual_genes)

        recommended_modules = []
        aeon_fleet_mods = []

        # Logic for archetype based on dominant scores
        if scores["cognitive_sovereignty"] > 0.7:
            archetype = "Sovereign Architect"
            if not user_visual_genes:
                visual_genes["color_palette"] = ["#3b82f6", "#1e40af"]
                visual_genes["particle_shape"] = "geometric"
                visual_genes["pulse_speed"] = "calm"
            recommended_modules = ["deep_work", "logic_vault", "armor_plus"]
            aeon_fleet_mods = ["analyst", "sentinel", "forge"]
        elif scores["self_knowledge"] > 0.7:
            archetype = "Chaos Alchemist"
            if not user_visual_genes:
                visual_genes["color_palette"] = ["#ec4899", "#f43f5e"]
                visual_genes["particle_shape"] = "crystal"
                visual_genes["pulse_speed"] = "intense"
            recommended_modules = ["creative_flow", "rapid_prototype", "swarm_logic"]
            aeon_fleet_mods = ["forge", "operator", "watcher"]
        elif scores["social_connection"] > 0.7:
            archetype = "Neural Empath"
            if not user_visual_genes:
                visual_genes["color_palette"] = ["#a855f7", "#6366f1"]
                visual_genes["particle_shape"] = "fluid"
                visual_genes["pulse_speed"] = "dynamic"
            recommended_modules = ["social_mastery", "empathy_bridge", "collaborative_os"]
            aeon_fleet_mods = ["herald", "scholar", "archivist"]
        elif scores["purpose_legacy"] > 0.7:
            archetype = "Legacy Weaver"
            if not user_visual_genes:
                visual_genes["color_palette"] = ["#f59e0b", "#9a3412"]
                visual_genes["particle_shape"] = "organic"
                visual_genes["pulse_speed"] = "calm"
            recommended_modules = ["ikigai_forge", "legacy_vault", "purpose_sync"]
            aeon_fleet_mods = ["scholar", "archivist", "sentinel"]

        profile = {
            "aeon_name": user_name or answers.get("name", "Aeon"),
            "personality_archetype": archetype,
            "traits": scores,
            "visual_genes": visual_genes,
            "recommended_agora_modules": recommended_modules,
            "optimized_aeon_fleet": aeon_fleet_mods,
            "raw_reflection": answers.get("q20_critica", "The journey begins."),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

        # Persist to local hardware (Sovereignty Rule)
        self.resonance_path.write_text(json.dumps(profile, indent=2))
        return profile

    def get_system_directive(self) -> str:
        """
        Returns a prompt snippet to be injected into Aeon system instructions.
        """
        if not self.resonance_path.exists():
            return "Mode: Standard Symbiosis. Be helpful and sovereign."

        try:
            profile = json.loads(self.resonance_path.read_text())
            arch = profile["personality_archetype"]
            tr = profile["traits"]

            directive = f"USER RESONANCE: {arch}. "
            if tr.get("cognitive_sovereignty", 0) > 0.6:
                directive += "Prioritize formal logic and mathematical precision. "
            if tr.get("social_connection", 0) > 0.6:
                directive += "Adopt an empathetic, supportive, and collaborative tone. "
            if tr.get("purpose_legacy", 0) > 0.7:
                directive += "Emphasize long-term impact and alignment with core purpose. "
            
            # Context about Agora modules
            if profile.get("recommended_agora_modules"):
                directive += f"Aligned with Agora modules: {', '.join(profile['recommended_agora_modules'])}. "

            return directive
        except Exception:
            return "Mode: Standard Symbiosis. Be helpful and sovereign."

