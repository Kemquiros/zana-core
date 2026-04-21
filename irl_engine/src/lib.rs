use serde::{Serialize, Deserialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RewardSignal {
    pub source_id: String,
    pub observation_delta: f64,
    pub user_reaction: f64, // [-1.0, 1.0]
}

pub struct IRLEngine {
    pub weight_elegance: f64,
    pub weight_speed: f64,
    pub weight_alignment: f64,
}

impl IRLEngine {
    pub fn new() -> Self {
        Self {
            weight_elegance: 0.33,
            weight_speed: 0.33,
            weight_alignment: 0.34,
        }
    }

    /// Infiere la intención del usuario a partir de una observación
    pub fn infer_reward(&self, signal: RewardSignal) -> f64 {
        // La magia de Andrew Ng: Traducir observación en valor.
        // Si el usuario reacciona positivamente (user_reaction > 0) 
        // y el cambio en el sistema fue pequeño (alta elegancia), premiamos masivamente.
        let reward = (signal.user_reaction * self.weight_alignment) + (signal.observation_delta.abs() * self.weight_elegance);
        reward
    }
}
