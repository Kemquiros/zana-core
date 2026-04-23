import json
from pathlib import Path
from typing import Dict, Any


class ResonanceEngine:
    """
    ZANA Resonance Engine — Transmutes user ritual answers into cognitive archetypes.
    This module bridges the human psyche with the Aeon's behavioral parameters,
    Aeon fleet configuration, and Agora module alignment.
    """

    def __init__(self, resonance_path: str = "data/resonance_profile.json"):
        self.resonance_path = Path(resonance_path)
        self.resonance_path.parent.mkdir(parents=True, exist_ok=True)

    def process_ritual(self, answers: Dict[str, str]) -> Dict[str, Any]:
        """
        Processes the 20 questions of the Resonance Ritual to forge the Aeon's identity.
        Determines the archetype, visual genes, and initial Agora module recommendations.
        """
        # Baseline traits (0.0 to 1.0)
        traits = {
            "sovereignty": 0.5,
            "logic": 0.5,
            "empathy": 0.5,
            "innovation": 0.5,
            "discipline": 0.5,
        }

        # --- ACT I: Sovereignty & Control ---
        if answers.get("q1") == "A":
            traits["discipline"] += 0.2
        elif answers.get("q1") == "E":
            traits["logic"] += 0.2
        elif answers.get("q1") == "F":
            traits["innovation"] += 0.2

        if answers.get("q2") == "A":
            traits["sovereignty"] += 0.2
        elif answers.get("q2") == "C":
            traits["empathy"] += 0.1

        # --- ACT II: Intellect & Style ---
        if answers.get("q6") == "A":
            traits["logic"] += 0.25
        elif answers.get("q6") == "B":
            traits["empathy"] += 0.25
        elif answers.get("q6") == "C":
            traits["innovation"] += 0.25

        # --- ARCHETYPE DETERMINATION ---
        # Normalize traits to [0, 1]
        for key in traits:
            traits[key] = max(0.0, min(1.0, traits[key]))

        archetype = "Digital Symbiont"
        visual_genes = {
            "color_palette": ["#4F46E5", "#7C3AED"],
            "pulse_speed": "dynamic",
            "particle_shape": "fluid",
        }
        
        recommended_modules = []
        aeon_fleet_mods = []

        if traits["logic"] > 0.7 and traits["sovereignty"] > 0.6:
            archetype = "Sovereign Architect"
            visual_genes["color_palette"] = ["#3b82f6", "#1e40af"]
            visual_genes["particle_shape"] = "geometric"
            visual_genes["pulse_speed"] = "calm"
            recommended_modules = ["deep_work", "logic_vault", "armor_plus"]
            aeon_fleet_mods = ["analyst", "sentinel", "forge"]
        elif traits["innovation"] > 0.7:
            archetype = "Chaos Alchemist"
            visual_genes["color_palette"] = ["#ec4899", "#f43f5e"]
            visual_genes["particle_shape"] = "crystal"
            visual_genes["pulse_speed"] = "intense"
            recommended_modules = ["creative_flow", "rapid_prototype", "swarm_logic"]
            aeon_fleet_mods = ["forge", "operator", "watcher"]
        elif traits["empathy"] > 0.7:
            archetype = "Neural Empath"
            visual_genes["color_palette"] = ["#a855f7", "#6366f1"]
            visual_genes["particle_shape"] = "fluid"
            visual_genes["pulse_speed"] = "dynamic"
            recommended_modules = ["social_mastery", "empathy_bridge", "collaborative_os"]
            aeon_fleet_mods = ["herald", "scholar", "archivist"]

        profile = {
            "personality_archetype": archetype,
            "traits": traits,
            "visual_genes": visual_genes,
            "recommended_agora_modules": recommended_modules,
            "optimized_aeon_fleet": aeon_fleet_mods,
            "raw_reflection": answers.get("q20_critica", "The journey begins."),
            "timestamp": "2026-04-22T00:00:00Z" # Will be updated dynamically
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
            if tr["logic"] > 0.6:
                directive += "Prioritize formal logic and mathematical precision. "
            if tr["empathy"] > 0.6:
                directive += "Adopt an empathetic, supportive, and collaborative tone. "
            if tr["sovereignty"] > 0.7:
                directive += "Emphasize data privacy and local-first principles in every advice. "
            
            # Context about Agora modules
            if profile.get("recommended_agora_modules"):
                directive += f"Aligned with Agora modules: {', '.join(profile['recommended_agora_modules'])}. "

            return directive
        except Exception:
            return "Mode: Standard Symbiosis. Be helpful and sovereign."
