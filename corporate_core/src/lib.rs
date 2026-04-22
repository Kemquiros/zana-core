use serde::{Serialize, Deserialize};
use chrono::{DateTime, Utc};
use std::collections::HashMap;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StrategicDecision {
    pub id: String,
    pub title: String,
    pub description: String,
    pub expected_roi: f64,
    pub vision_alignment: f64, // 0.0 to 1.0
    pub risk_factor: f64,
    pub status: String, // "PROPOSED", "APPROVED", "EXECUTED", "REJECTED"
    pub timestamp: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FinancialPulse {
    pub total_assets: f64,
    pub liquidity: f64,
    pub monthly_burn_rate: f64,
    pub revenue_growth: f64,
}

pub struct CorporateCore {
    pub vision_statement: String,
    pub proposed_decisions: Vec<StrategicDecision>,
    pub financial_pulse: FinancialPulse,
}

impl CorporateCore {
    pub fn new() -> Self {
        Self {
            vision_statement: "Expandir la soberanía humana a través de la inteligencia simbiótica.".to_string(),
            proposed_decisions: vec![],
            financial_pulse: FinancialPulse {
                total_assets: 1000000.0,
                liquidity: 250000.0,
                monthly_burn_rate: 15000.0,
                revenue_growth: 0.12,
            },
        }
    }

    /// Evalúa una propuesta de negocio y determina si el CxO-Aeon la recomienda
    pub fn evaluate_proposal(&mut self, title: &str, desc: &str, cost: f64, potential_gain: f64) -> StrategicDecision {
        let roi = (potential_gain - cost) / cost;
        
        // El CxO-Aeon prefiere proyectos con alto ROI y riesgo moderado
        let risk = if roi > 2.0 { 0.8 } else { 0.3 };
        
        // Simulación de alineamiento con la visión (usando lógica difusa interna)
        let alignment = if desc.to_lowercase().contains("soberanía") || desc.to_lowercase().contains("simbiosis") {
            0.95
        } else {
            0.60
        };

        let decision = StrategicDecision {
            id: uuid::Uuid::new_v4().to_string(),
            title: title.to_string(),
            description: desc.to_string(),
            expected_roi: roi,
            vision_alignment: alignment,
            risk_factor: risk,
            status: "PROPOSED".to_string(),
            timestamp: Utc::now(),
        };

        self.proposed_decisions.push(decision.clone());
        decision
    }

    /// Actualiza el estado de una decisión estratégica
    pub fn update_decision(&mut self, id: &str, new_status: &str) -> bool {
        if let Some(d) = self.proposed_decisions.iter_mut().find(|d| d.id == id) {
            d.status = new_status.to_string();
            return true;
        }
        false
    }
}
