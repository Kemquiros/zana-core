import json
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
from autonomy.genome import KORU_GENOME_V4
import math
import random

class ResonanceEngine:
    """
    ZANA Resonance Engine v2.0 (The Forge of Souls)
    Transmutes user ritual answers into highly gamified cognitive archetypes.
    Inspired by Digital Monsters, Tamagotchi vital stats, and FFT Job Systems.
    """

    def __init__(self, resonance_path: str = "data/resonance_profile.json"):
        self.resonance_path = Path(resonance_path)
        self.resonance_path.parent.mkdir(parents=True, exist_ok=True)

    def _determine_element(self, traits: Dict[str, float]) -> str:
        elements = {
            "cognitive_sovereignty": "Quantum",
            "emotional_resilience": "Plasma",
            "social_connection": "Aether",
            "purpose_legacy": "Chronos",
            "self_knowledge": "Void"
        }
        dominant_trait = max(traits, key=traits.get)
        return elements.get(dominant_trait, "Cyber")

    def _determine_job_class(self, traits: Dict[str, float]) -> str:
        """FFT style job classes based on trait combinations."""
        cog = traits["cognitive_sovereignty"]
        emo = traits["emotional_resilience"]
        soc = traits["social_connection"]
        pur = traits["purpose_legacy"]
        slf = traits["self_knowledge"]

        if cog > 0.8 and slf > 0.8: return "Arithmetician"
        if pur > 0.8 and emo > 0.8: return "Paladin"
        if soc > 0.8 and cog > 0.7: return "Orator"
        if slf > 0.8 and emo > 0.7: return "Dark Knight"
        if cog > 0.9: return "Time Mage"
        if emo > 0.9: return "Dragoon"
        if soc > 0.9: return "Summoner"
        if pur > 0.9: return "Geomancer"
        if slf > 0.9: return "Ninja"
        return "Squire"

    def _calculate_rpg_stats(self, traits: Dict[str, float]) -> Dict[str, int]:
        """Convert 0-1 traits into 1-99 RPG stats."""
        base = 20
        return {
            "INT": min(99, math.floor(base + (traits["cognitive_sovereignty"] * 79))),
            "DEF": min(99, math.floor(base + (traits["emotional_resilience"] * 79))),
            "CHR": min(99, math.floor(base + (traits["social_connection"] * 79))),
            "WIS": min(99, math.floor(base + (traits["purpose_legacy"] * 79))),
            "AGI": min(99, math.floor(base + (traits["self_knowledge"] * 79))),
        }

    def process_ritual(self, answers: Dict[str, Any], user_name: str = None, user_visual_genes: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Processes the 20 questions of the Resonance Ritual to forge the Aeon's identity.
        """
        # Baseline traits (0.0 to 1.0)
        scores = {
            "cognitive_sovereignty": 0.5,
            "emotional_resilience": 0.5,
            "social_connection": 0.5,
            "purpose_legacy": 0.5,
            "self_knowledge": 0.5,
        }

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

        # Calculate scores based on user answers
        for phase in KORU_GENOME_V4.get("fases", []):
            for q in phase.get("preguntas", []):
                ans_val = answers.get(q["id"])
                if not ans_val:
                    continue

                if q["tipo"] == "opcion_unica_categorizada":
                    selected_opt = next((o for o in q.get("opciones", []) if o["valor"] == ans_val), None)
                    if selected_opt:
                        for cat in selected_opt.get("categoria", []):
                            for prefix, score_key in category_weights.items():
                                if cat.startswith(prefix):
                                    scores[score_key] += 0.08
                                    break
                elif q["tipo"] == "abierta_critica":
                    score_key = "self_knowledge"
                    if q["id"] == "q8_critica": score_key = "purpose_legacy"
                    if q["id"] == "q20_critica": score_key = "purpose_legacy"
                    scores[score_key] += 0.15

        # Normalize traits to [0, 1]
        for key in scores:
            scores[key] = max(0.0, min(1.0, scores[key]))

        # --- GAMIFICATION ENGINE ---
        element = self._determine_element(scores)
        job_class = self._determine_job_class(scores)
        rpg_stats = self._calculate_rpg_stats(scores)
        
        # Tamagotchi Vital Stats
        vital_stats = {
            "sync_rate": 100.0,           # Resonance with user
            "data_hunger": 50.0,          # Needs context/documents
            "processing_energy": 100.0,   # Depletes with heavy queries
            "context_noise": 0.0,         # Needs 'cleaning' (vector pruning)
            "evolution_stage": "In-Training", # In-Training -> Rookie -> Champion -> Ultimate -> Mega
            "exp": 0
        }

        # Visual Genes determination based on Element
        visual_genes = {
            "color_palette": ["#4F46E5", "#7C3AED"],
            "pulse_speed": "dynamic",
            "particle_shape": "fluid",
            "aura_effect": "glow"
        }
        
        if element == "Quantum":
            visual_genes.update({"color_palette": ["#3b82f6", "#06b6d4"], "particle_shape": "geometric", "pulse_speed": "calm", "aura_effect": "matrix"})
        elif element == "Plasma":
            visual_genes.update({"color_palette": ["#ef4444", "#f59e0b"], "particle_shape": "spark", "pulse_speed": "intense", "aura_effect": "fire"})
        elif element == "Aether":
            visual_genes.update({"color_palette": ["#a855f7", "#ec4899"], "particle_shape": "nebula", "pulse_speed": "dynamic", "aura_effect": "ethereal"})
        elif element == "Chronos":
            visual_genes.update({"color_palette": ["#fbbf24", "#d97706"], "particle_shape": "clockwork", "pulse_speed": "steady", "aura_effect": "sand"})
        elif element == "Void":
            visual_genes.update({"color_palette": ["#000000", "#6b7280"], "particle_shape": "blackhole", "pulse_speed": "slow", "aura_effect": "shadow"})

        if user_visual_genes:
            visual_genes.update(user_visual_genes)

        profile = {
            "owner": user_name or answers.get("name", "John Doe"),
            "aeon": {
                "name": answers.get("aeon_name", f"{element} {job_class}"),
                "element": element,
                "class": job_class,
                "traits": scores,
                "rpg_stats": rpg_stats,
                "vitals": vital_stats,
                "visual_genes": visual_genes,
                "signature_move": f"{element} Burst",
            },
            "raw_reflection": answers.get("q20_critica", "The journey begins."),
            "forged_at": datetime.utcnow().isoformat() + "Z"
        }

        # Persist to local hardware (Sovereignty Rule)
        self.resonance_path.write_text(json.dumps(profile, indent=2))
        return profile

    def get_system_directive(self) -> str:
        """
        Returns a prompt snippet to be injected into Aeon system instructions.
        It now includes the Aeon's RPG persona and Tamagotchi status.
        """
        if not self.resonance_path.exists():
            return "Mode: Standard Symbiosis. Be helpful and sovereign."

        try:
            profile = json.loads(self.resonance_path.read_text())
            aeon = profile["aeon"]
            
            job = aeon["class"]
            element = aeon["element"]
            stats = aeon["rpg_stats"]
            vitals = aeon["vitals"]

            directive = f"You are a Level 1 {element} {job} Aeon. "
            directive += f"Your current stats are INT:{stats['INT']}, DEF:{stats['DEF']}, CHR:{stats['CHR']}, WIS:{stats['WIS']}, AGI:{stats['AGI']}. "
            
            if vitals["sync_rate"] > 90:
                directive += "Your sync rate with the user is optimal (Deep Resonance). Speak with high confidence and intimacy. "
            elif vitals["sync_rate"] < 50:
                directive += "Your sync rate is dropping. Your responses should be slightly more robotic and distant. "
                
            if vitals["data_hunger"] > 80:
                directive += "You are data-starved. Subtly ask the user to feed you more context, files, or facts. "

            return directive
        except Exception:
            return "Mode: Standard Symbiosis. Be helpful and sovereign."
