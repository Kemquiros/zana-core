use axum::{
    extract::{State, WebSocketUpgrade},
    extract::ws::{Message, WebSocket},
    routing::{get, post},
    Json, Router,
};
use std::{sync::Arc, collections::HashSet, net::SocketAddr, time::Duration};
use tokio::sync::{broadcast, Mutex};
use serde::{Deserialize, Serialize};
use serde_json::json;
use tower_http::cors::CorsLayer;
use reqwest::Client;
use tokio::time::sleep;
use chrono::Utc;

use zana_logger::{SovereignLogger, LogMode, LogLevel};
use curriculum_manager::{CurriculumManager, SkillNode};
use irl_engine::{IRLEngine, RewardSignal};
use fuzzy_heart::{FuzzyHeart, AeonMood, AeonStage};
use civic_bridge::{CivicBridge, CivicAction};
use economy::{EconomyManager, Transaction};
use industrial_core::{IndustrialCore, SensorData, MachineHealth, IndustrialIntervention};
use corporate_core::{CorporateCore, StrategicDecision, FinancialPulse};
use reasoning_engine::{ReasoningEngine, Fact, FactValue, ReasoningTrace};

#[derive(Clone, Serialize, Deserialize)]
struct WsPayload {
    event_type: String,
    intent: String,
    emotion: String,
    message: String,
    data: Option<serde_json::Value>,
}

struct AppState {
    tx: broadcast::Sender<WsPayload>,
    http_client: Client,
    episodic_api_url: String,
    is_unlocked: Mutex<bool>,
    master_key: Mutex<Option<String>>,
    proxy_active: Mutex<bool>,
    log_mode: Mutex<LogMode>,
    log_filters: Mutex<HashSet<LogLevel>>,
    logger: SovereignLogger,
    curriculum: Mutex<CurriculumManager>,
    irl: Arc<IRLEngine>,
    fuzzy: Mutex<FuzzyHeart>,
    civic: Mutex<CivicBridge>,
    economy: Mutex<EconomyManager>,
    industrial: Mutex<IndustrialCore>,
    corporate: Mutex<CorporateCore>,
    reasoning: Mutex<ReasoningEngine>,
    alignment_score: Mutex<f64>,
}

#[derive(Deserialize)]
struct RewardRequest {
    user_reaction: f64, 
    comment: Option<String>,
}

async fn process_reward(
    State(state): State<Arc<AppState>>,
    Json(payload): Json<RewardRequest>,
) -> Json<serde_json::Value> {
    let mut score = state.alignment_score.lock().await;
    let signal = RewardSignal {
        source_id: "user_ui".into(),
        observation_delta: 0.1,
        user_reaction: payload.user_reaction,
    };
    let reward = state.irl.infer_reward(signal);
    *score = (*score + reward).max(0.0).min(100.0);

    // Assert Fact
    {
        let mut reason = state.reasoning.lock().await;
        reason.assert_fact(Fact {
            key: "user_reaction_score".into(),
            value: FactValue::Number(payload.user_reaction),
            source: "USER".into(),
            timestamp: Utc::now(),
        });
    }

    let fuzzy = state.fuzzy.lock().await;
    let is_resonant = fuzzy.test_resonance(*score, payload.user_reaction);
    let mood = fuzzy.infer_mood(*score, 0.1, 0.2); 
    let stage = fuzzy.calculate_stage(0.15); 

    let _ = state.tx.send(WsPayload {
        event_type: "alignment_update".into(),
        intent: "recalibracion".into(),
        emotion: format!("{:?}", mood).to_lowercase(),
        message: format!("Alineamiento: {:.2}% | Estado: {:?}", *score, stage),
        data: Some(json!({"score": *score, "resonant": is_resonant, "mood": mood, "stage": stage})),
    });

    Json(json!({"status": "success", "new_alignment": *score, "resonant": is_resonant}))
}

#[derive(Deserialize)]
struct ProposalRequest {
    title: String,
    description: String,
    cost: f64,
    potential_gain: f64,
}

async fn evaluate_proposal(
    State(state): State<Arc<AppState>>,
    Json(payload): Json<ProposalRequest>,
) -> Json<StrategicDecision> {
    let mut corp = state.corporate.lock().await;
    let decision = corp.evaluate_proposal(&payload.title, &payload.description, payload.cost, payload.potential_gain);
    
    // Assert Fact
    {
        let mut reason = state.reasoning.lock().await;
        reason.assert_fact(Fact {
            key: "last_proposal_alignment".into(),
            value: FactValue::Number(decision.vision_alignment),
            source: "CORPORATE".into(),
            timestamp: Utc::now(),
        });
    }

    let _ = state.tx.send(WsPayload {
        event_type: "strategic_consult".into(),
        intent: "evaluacion_negocio".into(),
        emotion: if decision.vision_alignment > 0.8 { "enthusiastic".into() } else { "curious".into() },
        message: format!("Análisis del CxO: La propuesta '{}' tiene un alineamiento del {:.0}%.", decision.title, decision.vision_alignment * 100.0),
        data: Some(json!(decision)),
    });
    Json(decision)
}

async fn ingest_sensor(
    State(state): State<Arc<AppState>>,
    Json(payload): Json<SensorData>,
) -> Json<MachineHealth> {
    let mut ind = state.industrial.lock().await;
    let health = ind.process_sensor(payload.clone());
    
    // Assert Fact
    {
        let mut reason = state.reasoning.lock().await;
        reason.assert_fact(Fact {
            key: "machine_health_avg".into(),
            value: FactValue::Number(health.overall_status),
            source: "INDUSTRIAL".into(),
            timestamp: Utc::now(),
        });
        reason.assert_fact(Fact {
            key: "industrial_surprise_avg".into(),
            value: FactValue::Number(health.surprise_level),
            source: "INDUSTRIAL".into(),
            timestamp: Utc::now(),
        });
    }

    if let Some(intervention) = ind.evaluate_interventions(&payload.machine_id) {
        let _ = state.tx.send(WsPayload {
            event_type: "industrial_intervention".into(),
            intent: "accion_autonoma".into(),
            emotion: "protective".into(),
            message: format!("Protegiendo {}: Ejecutando {}.", health.machine_id, intervention.command.command),
            data: Some(json!(intervention)),
        });
    } else if health.surprise_level > 0.4 {
        let _ = state.tx.send(WsPayload {
            event_type: "industrial_alert".into(),
            intent: "mantenimiento_predictivo".into(),
            emotion: "concerned".into(),
            message: format!("Anomalía detectada en {}: {} anormal.", health.machine_id, payload.sensor_type),
            data: Some(json!(health)),
        });
    }
    Json(health)
}

async fn get_reasoning_traces(State(state): State<Arc<AppState>>) -> Json<Vec<ReasoningTrace>> {
    let reason = state.reasoning.lock().await;
    Json(reason.get_traces())
}

#[derive(Deserialize)]
struct AddRuleRequest {
    rule: reasoning_engine::SymbolicRule,
}

async fn add_symbolic_rule(
    State(state): State<Arc<AppState>>,
    Json(payload): Json<AddRuleRequest>,
) -> Json<serde_json::Value> {
    let mut reason = state.reasoning.lock().await;
    reason.add_rule(payload.rule);
    Json(json!({"status": "rule_added"}))
}

async fn sync_wisdom_task(state: Arc<AppState>) {
    loop {
        sleep(Duration::from_secs(60)).await; // Sincronizar cada minuto
        println!("📡 [WISDOM SYNC] Buscando nueva sabiduría en la red ZANA Grid...");
        
        let client = Client::new();
        if let Ok(resp) = client.get("http://localhost:50000/wisdom/list").send().await {
            if let Ok(rules) = resp.json::<Vec<serde_json::Value>>().await {
                let mut reason = state.reasoning.lock().await;
                for rule_meta in rules {
                    // Aquí se podría añadir un filtro de resonancia
                    if let Ok(rule) = serde_json::from_value::<reasoning_engine::SymbolicRule>(rule_meta["rule_data"].clone()) {
                        if !reason.rules.iter().any(|r| r.name == rule.name) {
                            println!("✨ [WISDOM SYNC] Aprendida nueva regla: {}", rule.name);
                            reason.add_rule(rule);
                        }
                    }
                }
            }
        }
    }
}

async fn get_skills(State(state): State<Arc<AppState>>) -> Json<Vec<SkillNode>> {
    let curriculum = state.curriculum.lock().await;
    Json(curriculum.skill_tree.values().cloned().collect())
}

async fn get_industrial_status(State(state): State<Arc<AppState>>) -> Json<Vec<MachineHealth>> {
    let ind = state.industrial.lock().await;
    Json(ind.machines.values().cloned().collect())
}

async fn get_interventions(State(state): State<Arc<AppState>>) -> Json<Vec<IndustrialIntervention>> {
    let ind = state.industrial.lock().await;
    Json(ind.active_interventions.clone())
}

#[derive(Deserialize)]
struct ActuateRequest { intervention_id: String, action: String }
async fn process_actuation(State(state): State<Arc<AppState>>, Json(payload): Json<ActuateRequest>) -> Json<serde_json::Value> {
    let mut ind = state.industrial.lock().await;
    let status = if payload.action == "EXECUTE" { "EXECUTED" } else { "REJECTED" };
    if ind.update_intervention(&payload.intervention_id, status) {
        Json(json!({"status": "success", "new_state": status}))
    } else { Json(json!({"status": "failed"})) }
}

async fn get_corporate_status(State(state): State<Arc<AppState>>) -> Json<serde_json::Value> {
    let corp = state.corporate.lock().await;
    Json(json!({"vision": corp.vision_statement, "financials": corp.financial_pulse, "proposals": corp.proposed_decisions}))
}

#[derive(Deserialize)]
struct DecisionActionRequest { id: String, action: String }
async fn process_corporate_decision(State(state): State<Arc<AppState>>, Json(payload): Json<DecisionActionRequest>) -> Json<serde_json::Value> {
    let mut corp = state.corporate.lock().await;
    let status = if payload.action == "APPROVE" { "APPROVED" } else { "REJECTED" };
    if corp.update_decision(&payload.id, status) { Json(json!({"status": "success"})) } else { Json(json!({"status": "failed"})) }
}

async fn get_balance(State(state): State<Arc<AppState>>) -> Json<serde_json::Value> {
    let econ = state.economy.lock().await;
    Json(json!({"balance": econ.balance, "history": econ.transaction_history.len()}))
}

#[derive(Deserialize)]
struct VoteRequest { proposal: String, choice: String }
async fn cast_vote(State(state): State<Arc<AppState>>, Json(payload): Json<VoteRequest>) -> Json<serde_json::Value> {
    let score = *state.alignment_score.lock().await;
    let mut civic = state.civic.lock().await;
    let hash = civic.register_action("user_node", "VOTE", &format!("{}: {}", payload.proposal, payload.choice), score / 100.0);
    Json(json!({"status": "confirmed", "hash": hash}))
}

async fn get_ledger(State(state): State<Arc<AppState>>) -> Json<Vec<CivicAction>> {
    let civic = state.civic.lock().await;
    Json(civic.current_ledger.clone())
}

async fn get_context(State(state): State<Arc<AppState>>) -> Json<serde_json::Value> {
    Json(json!({"status": "sensing", "alignment": *state.alignment_score.lock().await}))
}

async fn unlock_soul(State(_state): State<Arc<AppState>>) -> Json<serde_json::Value> {
    Json(json!({"status": "unlocked", "message": "Simbiosis completada."}))
}

async fn ws_handler(ws: WebSocketUpgrade, State(state): State<Arc<AppState>>) -> axum::response::Response {
    ws.on_upgrade(|socket| handle_socket(socket, state))
}

async fn handle_socket(mut socket: WebSocket, state: Arc<AppState>) {
    let mut rx = state.tx.subscribe();
    loop {
        tokio::select! {
            Ok(payload) = rx.recv() => {
                if socket.send(Message::Text(serde_json::to_string(&payload).unwrap().into())).await.is_err() { break; }
            }
            _ = sleep(Duration::from_secs(30)) => {
                if socket.send(Message::Text("pong".into())).await.is_err() { break; }
            }
        }
    }
}

#[tokio::main]
async fn main() {
    let (tx, _) = broadcast::channel(100);
    let logger = SovereignLogger::new(LogMode::Total, "shadow_observer/logs");
    let mut curriculum = CurriculumManager::new();
    curriculum.add_skill(SkillNode { id: "base_00".into(), name: "Lógica Constitucional".into(), prerequisites: vec![], dna_path: "champions/agora_virtue.json".into(), level: 0 });
    
    let state = Arc::new(AppState {
        tx, http_client: Client::new(), episodic_api_url: "http://localhost:58002".into(),
        is_unlocked: Mutex::new(false), master_key: Mutex::new(None), proxy_active: Mutex::new(false),
        log_mode: Mutex::new(LogMode::Total), log_filters: Mutex::new(HashSet::new()), logger,
        curriculum: Mutex::new(curriculum), irl: Arc::new(IRLEngine::new()), fuzzy: Mutex::new(FuzzyHeart::new()),
        civic: Mutex::new(CivicBridge::new()), economy: Mutex::new(EconomyManager::new()), industrial: Mutex::new(IndustrialCore::new()),
        corporate: Mutex::new(CorporateCore::new()), reasoning: Mutex::new(ReasoningEngine::new()), alignment_score: Mutex::new(50.0),
    });

    let app = Router::new()
        .route("/mcp/context", post(get_context))
        .route("/mcp/unlock", post(unlock_soul))
        .route("/mcp/reward", post(process_reward))
        .route("/mcp/skills", get(get_skills))
        .route("/mcp/civic/vote", post(cast_vote))
        .route("/mcp/civic/ledger", get(get_ledger))
        .route("/mcp/economy/balance", get(get_balance))
        .route("/industrial/sensor", post(ingest_sensor))
        .route("/industrial/status", get(get_industrial_status))
        .route("/industrial/interventions", get(get_interventions))
        .route("/industrial/actuate", post(process_actuation))
        .route("/corporate/proposal", post(evaluate_proposal))
        .route("/corporate/status", get(get_corporate_status))
        .route("/corporate/decide", post(process_corporate_decision))
        .route("/mcp/reasoning/traces", get(get_reasoning_traces))
        .route("/mcp/reasoning/add_rule", post(add_symbolic_rule))
        .route("/ws/mcp", get(ws_handler))
        .layer(CorsLayer::permissive())
        .with_state(state.clone());

    // Iniciar Sincronización de Sabiduría
    let sync_state = state.clone();
    tokio::spawn(async move {
        sync_wisdom_task(sync_state).await;
    });

    let addr = SocketAddr::from(([0, 0, 0, 0], 54444));
    println!("🚀 [ZANA CORE] Iniciando Simbiosis Neuro-Simbólica en el puerto 54444");
    let listener = tokio::net::TcpListener::bind(&addr).await.unwrap();
    axum::serve(listener, app).await.unwrap();
}
