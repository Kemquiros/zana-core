use serde::{Serialize, Deserialize};
use std::collections::{HashMap, VecDeque};
use chrono::{DateTime, Utc};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum FactValue {
    String(String),
    Number(f64),
    Boolean(bool),
    Object(HashMap<String, FactValue>), // Soporte para DefTemplates (objetos estructurados)
    List(Vec<FactValue>),
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Fact {
    pub key: String,
    pub value: FactValue,
    pub source: String,
    pub timestamp: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ReasoningTrace {
    pub rule_name: String,
    pub deduction: String,
    pub explanation: String, // Explicabilidad profunda
    pub timestamp: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum Operator {
    Eq, Neq, Gt, Lt, Gte, Lte, Contains,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Condition {
    pub fact_key: String,
    pub field_path: Option<String>, // Para objetos estructurados: ej. "temp" en una máquina
    pub operator: Operator,
    pub value: FactValue,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum Action {
    EmitEffect(String),
    AssertFact(String, FactValue),
    LogTrace(String),
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SymbolicRule {
    pub name: String,
    pub conditions: Vec<Condition>,
    pub actions: Vec<Action>,
    pub explanation_template: String,
}

pub struct ReasoningEngine {
    pub knowledge_base: HashMap<String, Fact>,
    pub rules: Vec<SymbolicRule>,
    pub traces: VecDeque<ReasoningTrace>,
    pub max_traces: usize,
}

impl ReasoningEngine {
    pub fn new() -> Self {
        let mut engine = Self {
            knowledge_base: HashMap::new(),
            rules: vec![],
            traces: VecDeque::new(),
            max_traces: 50,
        };
        engine.load_default_rules();
        engine
    }

    fn load_default_rules(&mut self) {
        // Regla de Supervivencia (Evolucionada)
        self.rules.push(SymbolicRule {
            name: "Empire_Survival_v2".to_string(),
            conditions: vec![
                Condition {
                    fact_key: "machine_health_avg".to_string(),
                    field_path: None,
                    operator: Operator::Lt,
                    value: FactValue::Number(0.4),
                },
                Condition {
                    fact_key: "liquidity".to_string(),
                    field_path: None,
                    operator: Operator::Lt,
                    value: FactValue::Number(50000.0),
                },
            ],
            actions: vec![
                Action::EmitEffect("LOCK_EXPENSES".to_string()),
                Action::LogTrace("Iniciando Protocolo de Austeridad por colapso industrial.".to_string()),
            ],
            explanation_template: "DEDUCCIÓN: Salud industrial ({machine_health_avg}) crítica y liquidez ({liquidity}) insuficiente.".to_string(),
        });

        // Regla de Sabiduría Global (Hito 7.2 PREP)
        self.rules.push(SymbolicRule {
            name: "Wisdom_Threshold".to_string(),
            conditions: vec![
                Condition {
                    fact_key: "active_peers".to_string(),
                    field_path: None,
                    operator: Operator::Gte,
                    value: FactValue::Number(5.0),
                }
            ],
            actions: vec![
                Action::EmitEffect("SYNC_COMMUNITY_RULES".to_string()),
            ],
            explanation_template: "Enjambre detectado ({} nodos). Sincronizando sabiduría comunitaria.".to_string(),
        });

        // REGLA: Reflexión Agéntica (Hito 7.3)
        self.rules.push(SymbolicRule {
            name: "Self_Critique_Pattern".to_string(),
            conditions: vec![
                Condition {
                    fact_key: "last_action_status".to_string(),
                    field_path: None,
                    operator: Operator::Eq,
                    value: FactValue::String("FAILED".to_string()),
                }
            ],
            actions: vec![
                Action::LogTrace("ERROR DETECTADO: Iniciando bucle de reflexión para ajustar estrategia.".to_string()),
                Action::EmitEffect("TRIGGER_REPLANNING".to_string()),
            ],
            explanation_template: "Falla en acción previa detectada. El sistema está auto-criticando su plan actual.".to_string(),
        });
    }

    pub fn assert_fact(&mut self, fact: Fact) -> Vec<String> {
        self.knowledge_base.insert(fact.key.clone(), fact);
        self.evaluate_rules()
    }

    pub fn evaluate_rules(&mut self) -> Vec<String> {
        let mut effects = vec![];
        let mut new_facts = vec![];
        let mut triggered_traces = vec![];

        for rule in &self.rules {
            let mut all_match = true;
            for cond in &rule.conditions {
                if !self.check_condition(cond) {
                    all_match = false;
                    break;
                }
            }

            if all_match {
                // Ejecutar acciones
                for action in &rule.actions {
                    match action {
                        Action::EmitEffect(e) => effects.push(e.clone()),
                        Action::AssertFact(k, v) => new_facts.push((k.clone(), v.clone())),
                        Action::LogTrace(msg) => {
                            triggered_traces.push((rule.name.clone(), msg.clone(), rule.explanation_template.clone()));
                        }
                    }
                }
            }
        }

        // Registrar rastros
        for (name, deduction, explanation) in triggered_traces {
            self.add_trace(&name, &deduction, &explanation);
        }

        // Recursividad limitada (para evitar bucles infinitos en esta versión simple)
        if !new_facts.is_empty() {
             for (k, v) in new_facts {
                 self.knowledge_base.insert(k.clone(), Fact {
                     key: k,
                     value: v,
                     source: "REASONING_ENGINE".into(),
                     timestamp: Utc::now(),
                 });
             }
             // effects.extend(self.evaluate_rules()); // Comentado para evitar recursion infinita sin proteccion
        }

        effects
    }

    fn check_condition(&self, cond: &Condition) -> bool {
        let fact = match self.knowledge_base.get(&cond.fact_key) {
            Some(f) => f,
            None => return false,
        };

        let current_val = match &cond.field_path {
            Some(path) => {
                if let FactValue::Object(map) = &fact.value {
                    match map.get(path) {
                        Some(v) => v,
                        None => return false,
                    }
                } else { return false; }
            },
            None => &fact.value,
        };

        match (&cond.operator, current_val, &cond.value) {
            (Operator::Eq, a, b) => a == b,
            (Operator::Neq, a, b) => a != b,
            (Operator::Gt, FactValue::Number(a), FactValue::Number(b)) => a > b,
            (Operator::Lt, FactValue::Number(a), FactValue::Number(b)) => a < b,
            (Operator::Gte, FactValue::Number(a), FactValue::Number(b)) => a >= b,
            (Operator::Lte, FactValue::Number(a), FactValue::Number(b)) => a <= b,
            _ => false,
        }
    }

    fn add_trace(&mut self, rule: &str, deduction: &str, explanation: &str) {
        if self.traces.len() >= self.max_traces { self.traces.pop_front(); }
        self.traces.push_back(ReasoningTrace {
            rule_name: rule.to_string(),
            deduction: deduction.to_string(),
            explanation: explanation.to_string(),
            timestamp: Utc::now(),
        });
        println!("🧠 [DEDUCTION] {} -> {}", rule, deduction);
    }

    pub fn get_traces(&self) -> Vec<ReasoningTrace> {
        self.traces.iter().cloned().collect()
    }

    pub fn add_rule(&mut self, rule: SymbolicRule) {
        self.rules.push(rule);
    }
}
