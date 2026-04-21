use chrono::{DateTime, Utc};
use serde::{Serialize, Deserialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Transaction {
    pub from: String,
    pub to: String,
    pub amount: f64,
    pub asset_id: String, // "RESONANCE_CREDIT" o ID de un Warrior
    pub memo: String,
}

pub struct EconomyManager {
    pub balance: f64,
    pub transaction_history: Vec<Transaction>,
    pub tax_rate: f64, // Peaje cognitivo para VECANOVA (30%)
}

impl EconomyManager {
    pub fn new() -> Self {
        Self {
            balance: 1000.0, // Créditos iniciales de cortesía
            transaction_history: vec![],
            tax_rate: 0.3,
        }
    }

    /// Procesa una recompensa por minería (Proof of Evolution)
    pub fn reward_mining(&mut self, fitness_gain: f64) {
        let reward = fitness_gain * 100.0;
        self.balance += reward;
        println!("💰 [ECONOMY] Recompensa PoE recibida: +{:.2} créditos", reward);
    }

    /// Transacción para comprar un ADN Warrior
    pub fn buy_dna(&mut self, cost: f64, dna_id: &str, seller: &str) -> bool {
        if self.balance >= cost {
            let tax = cost * self.tax_rate;
            let net = cost - tax;
            self.balance -= cost;

            self.transaction_history.push(Transaction {
                from: "user_local".to_string(),
                to: seller.to_string(),
                amount: net,
                asset_id: dna_id.to_string(),
                memo: format!("Purchase of Warrior DNA (Tax paid: {:.2})", tax),
            });
            return true;
        }
        false
    }
}

// ─── HITO 8.2: Evolución por Sabiduría — Mastery Map ────────────────────────
// Un Aeon acumula XP al asimilar reglas del Wisdom Hub y evoluciona de rango.

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, PartialOrd)]
pub enum AeonRank {
    Larva,      // 0–99 XP
    Initiate,   // 100–299 XP
    Warrior,    // 300–599 XP
    Champion,   // 600–999 XP
    Legend,     // 1000+ XP
}

impl AeonRank {
    pub fn from_xp(xp: u32) -> Self {
        match xp {
            0..=99    => AeonRank::Larva,
            100..=299 => AeonRank::Initiate,
            300..=599 => AeonRank::Warrior,
            600..=999 => AeonRank::Champion,
            _         => AeonRank::Legend,
        }
    }

    pub fn label(&self) -> &str {
        match self {
            AeonRank::Larva    => "Larva",
            AeonRank::Initiate => "Initiate",
            AeonRank::Warrior  => "Warrior",
            AeonRank::Champion => "Champion",
            AeonRank::Legend   => "Legend",
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum RuleTier {
    Common,    // +10 XP
    Rare,      // +25 XP
    Epic,      // +50 XP
    Legendary, // +100 XP
}

impl RuleTier {
    pub fn xp_value(&self) -> u32 {
        match self {
            RuleTier::Common    => 10,
            RuleTier::Rare      => 25,
            RuleTier::Epic      => 50,
            RuleTier::Legendary => 100,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MasteryEntry {
    pub rule_name: String,
    pub tier: RuleTier,
    pub xp_gained: u32,
    pub timestamp: DateTime<Utc>,
}

pub struct MasteryMap {
    pub aeon_id: String,
    pub total_xp: u32,
    pub current_rank: AeonRank,
    pub history: Vec<MasteryEntry>,
}

impl MasteryMap {
    pub fn new(aeon_id: &str) -> Self {
        Self {
            aeon_id: aeon_id.to_string(),
            total_xp: 0,
            current_rank: AeonRank::Larva,
            history: vec![],
        }
    }

    /// Asimila una regla del Wisdom Hub y concede XP.
    /// Devuelve `Some(new_rank)` si el Aeon evolucionó de rango.
    pub fn assimilate_rule(&mut self, rule_name: &str, tier: RuleTier) -> Option<AeonRank> {
        let xp = tier.xp_value();
        self.total_xp += xp;

        self.history.push(MasteryEntry {
            rule_name: rule_name.to_string(),
            tier,
            xp_gained: xp,
            timestamp: Utc::now(),
        });

        let new_rank = AeonRank::from_xp(self.total_xp);
        if new_rank != self.current_rank {
            let old = self.current_rank.label();
            let new_label = new_rank.label();
            println!("⚡ [MASTERY] Aeon '{}' evolved: {} → {} (XP: {})", self.aeon_id, old, new_label, self.total_xp);
            self.current_rank = new_rank.clone();
            return Some(new_rank);
        }

        println!("📚 [MASTERY] '{}' assimilated rule '{}' (+{} XP, total: {})",
            self.aeon_id, rule_name, xp, self.total_xp);
        None
    }

    pub fn summary(&self) -> serde_json::Value {
        serde_json::json!({
            "aeon_id": self.aeon_id,
            "rank": self.current_rank.label(),
            "total_xp": self.total_xp,
            "rules_assimilated": self.history.len(),
        })
    }
}
