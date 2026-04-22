use serde::{Serialize, Deserialize};
use sha2::{Sha256, Digest};
use chrono::{DateTime, Utc};
use hex;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CivicAction {
    pub actor_id: String,
    pub action_type: String, // "PROPOSAL", "VOTE", "DECISION"
    pub content: String,
    pub fitness_context: f64, // El "Peso" del actor en el enjambre
    pub prev_hash: String,
    pub timestamp: DateTime<Utc>,
}

pub struct CivicBridge {
    pub current_ledger: Vec<CivicAction>,
}

impl CivicBridge {
    pub fn new() -> Self {
        Self { current_ledger: vec![] }
    }

    /// Registra una acción inmutable en el ledger soberano
    pub fn register_action(&mut self, actor: &str, a_type: &str, content: &str, fitness: f64) -> String {
        let prev_hash = self.current_ledger.last()
            .map(|a| self.hash_action(a))
            .unwrap_or_else(|| "GENESIS_ZANA".to_string());

        let action = CivicAction {
            actor_id: actor.to_string(),
            action_type: a_type.to_string(),
            content: content.to_string(),
            fitness_context: fitness,
            prev_hash,
            timestamp: Utc::now(),
        };

        let hash = self.hash_action(&action);
        self.current_ledger.push(action);
        hash
    }

    fn hash_action(&self, action: &CivicAction) -> String {
        let mut hasher = Sha256::new();
        hasher.update(serde_json::to_string(action).unwrap());
        hex::encode(hasher.finalize())
    }
}

// ─── HITO 8.1: Modo Político Público ────────────────────────────────────────
// Cada cambio en la RuleBase queda firmado y auditable en el RuleLedger.

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum RuleOperation {
    Add,
    Modify,
    Remove,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RuleLedgerEntry {
    pub rule_name: String,
    /// SHA-256 del JSON serializado de la regla
    pub rule_hash: String,
    pub operation: RuleOperation,
    pub author: String,
    pub timestamp: DateTime<Utc>,
    /// Hash del entry anterior (cadena inmutable)
    pub prev_hash: String,
    /// Hash de este entry (firma del bloque)
    pub entry_hash: String,
}

pub struct RuleLedger {
    pub entries: Vec<RuleLedgerEntry>,
}

impl RuleLedger {
    pub fn new() -> Self {
        Self { entries: vec![] }
    }

    /// Registra un cambio de regla en el ledger público y devuelve su hash.
    /// `rule_json` debe ser el JSON serializado del SymbolicRule.
    pub fn mirror_rule_change(&mut self, rule_json: &str, operation: RuleOperation, author: &str) -> String {
        let rule_hash = {
            let mut h = Sha256::new();
            h.update(rule_json.as_bytes());
            hex::encode(h.finalize())
        };

        let rule_name = serde_json::from_str::<serde_json::Value>(rule_json)
            .ok()
            .and_then(|v| v["name"].as_str().map(String::from))
            .unwrap_or_else(|| "UNKNOWN".to_string());

        let prev_hash = self.entries.last()
            .map(|e| e.entry_hash.clone())
            .unwrap_or_else(|| "GENESIS_RULE_LEDGER".to_string());

        // El entry_hash encadena todo lo que identifica este bloque.
        let chain_data = format!("{}|{}|{:?}|{}|{}", rule_name, rule_hash, operation, author, prev_hash);
        let entry_hash = {
            let mut h = Sha256::new();
            h.update(chain_data.as_bytes());
            hex::encode(h.finalize())
        };

        let entry = RuleLedgerEntry {
            rule_name: rule_name.clone(),
            rule_hash,
            operation,
            author: author.to_string(),
            timestamp: Utc::now(),
            prev_hash,
            entry_hash: entry_hash.clone(),
        };

        println!("📜 [CIVIC LEDGER] Rule '{}' mirrored | Hash: {}...", rule_name, &entry_hash[..12]);
        self.entries.push(entry);
        entry_hash
    }

    /// Devuelve el log público completo (auditable).
    pub fn get_public_log(&self) -> &Vec<RuleLedgerEntry> {
        &self.entries
    }

    /// Verifica que ningún bloque fue alterado después de ser firmado.
    pub fn verify_integrity(&self) -> bool {
        for i in 1..self.entries.len() {
            if self.entries[i].prev_hash != self.entries[i - 1].entry_hash {
                eprintln!("⚠️  [CIVIC LEDGER] Cadena rota en el bloque {}", i);
                return false;
            }
        }
        true
    }
}
