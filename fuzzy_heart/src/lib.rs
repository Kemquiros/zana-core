use serde::{Serialize, Deserialize};
use std::collections::HashMap;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum AeonMood {
    Dormant,
    Curious,
    Enthusiastic,
    Concerned,
    Confused,
    Resonant,
    Apex,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum AeonStage {
    Seed,      // Huevo / Semilla
    Larva,     // Tamagotchi inicial
    Warrior,   // Digimon Campeón
    Aeon,      // Entidad Protectora
    Singularity, // Fusión total
}

pub struct FuzzyHeart {
    pub resonance_threshold: f64,
    pub emotional_inertia: f64, // Qué tan rápido cambian los sentimientos
    pub current_resonance: f64,
}

impl FuzzyHeart {
    pub fn new() -> Self {
        Self {
            resonance_threshold: 75.0,
            emotional_inertia: 0.1,
            current_resonance: 50.0,
        }
    }

    /// TEST DE RESONANCIA: El puente entre el IRL (intención) y el Corazón (emoción)
    /// Valida si el "sentimiento" del Aeon está alineado con la "recompensa" del usuario.
    pub fn test_resonance(&self, alignment_score: f64, user_reward: f64) -> bool {
        // Un test de resonancia exitoso significa que:
        // 1. El alineamiento es alto (> threshold)
        // 2. El cambio (reward) es positivo.
        alignment_score >= self.resonance_threshold && user_reward >= 0.0
    }

    /// Inferencia Difusa para determinar el humor
    pub fn infer_mood(&self, alignment: f64, surprise: f64, progress: f64) -> AeonMood {
        // Lógica Difusa simplificada:
        // SI Alineamiento es ALTO y Sorpresa es BAJA -> RESONANTE
        // SI Alineamiento es BAJO y Sorpresa es ALTA -> CONFUNDIDO
        // SI Progreso es MUY ALTO -> ENTUSIASTA
        
        if alignment > 90.0 { return AeonMood::Apex; }
        if alignment > 75.0 { return AeonMood::Resonant; }
        if surprise > 0.8 { return AeonMood::Confused; }
        if progress > 0.7 { return AeonMood::Enthusiastic; }
        if alignment < 30.0 { return AeonMood::Concerned; }
        
        AeonMood::Curious
    }

    /// Determina la etapa evolutiva basada en la Maestría (Curriculum)
    pub fn calculate_stage(&self, total_mastery: f64) -> AeonStage {
        if total_mastery > 0.9 { return AeonStage::Singularity; }
        if total_mastery > 0.7 { return AeonStage::Aeon; }
        if total_mastery > 0.4 { return AeonStage::Warrior; }
        if total_mastery > 0.1 { return AeonStage::Larva; }
        AeonStage::Seed
    }
}
