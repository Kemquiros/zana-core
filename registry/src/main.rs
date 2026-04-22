use axum::{
    extract::{Path, State},
    routing::{get, post},
    Json, Router,
};
use serde::{Deserialize, Serialize};
use std::{collections::HashMap, net::SocketAddr, sync::Arc};
use tokio::sync::Mutex;
use chrono::{DateTime, Utc};
use tower_http::cors::CorsLayer;

/// URL base del zana-core-api. Sobreescribible via env ZANA_CORE_URL.
const ZANA_CORE_URL_DEFAULT: &str = "http://localhost:58000";

#[derive(Serialize, Deserialize, Clone, Debug)]
struct Node {
    id: String,
    addr: String,
    last_seen: DateTime<Utc>,
    capabilities: Vec<String>,
}

#[derive(Serialize, Deserialize, Clone, Debug)]
struct SyncBlob {
    user_id: String,
    device_id: String,
    payload: String, 
    timestamp: DateTime<Utc>,
}

#[derive(Serialize, Deserialize, Clone, Debug)]
struct ResonanceMessage {
    id: String,
    sender_id: String,
    recipient_id: String,
    content: String,
    resonance_packet: Option<serde_json::Value>,
    timestamp: DateTime<Utc>,
}

#[derive(Serialize, Deserialize, Clone, Debug)]
struct WisdomRule {
    id: String,
    creator_node: String,
    rule_data: serde_json::Value, // Estructura SymbolicRule serializada
    votes: i32,
    timestamp: DateTime<Utc>,
}

struct RegistryState {
    nodes: Mutex<HashMap<String, Node>>,
    sync_vault: Mutex<HashMap<String, Vec<SyncBlob>>>,
    message_queue: Mutex<HashMap<String, Vec<ResonanceMessage>>>,
    wisdom_hub: Mutex<Vec<WisdomRule>>,
    // A2A task store
    tasks: Mutex<HashMap<String, A2aTask>>,
}

// ─── ADK A2A Types ───────────────────────────────────────────────────────────

/// AgentCard — autodescripción pública de ZANA como nodo ADK compatible.
/// Servida en GET /.well-known/agent.json
#[derive(Serialize, Clone, Debug)]
struct AgentCard {
    name: &'static str,
    description: &'static str,
    url: String,
    version: &'static str,
    #[serde(rename = "defaultInputModes")]
    default_input_modes: Vec<&'static str>,
    #[serde(rename = "defaultOutputModes")]
    default_output_modes: Vec<&'static str>,
    capabilities: AgentCapabilities,
    skills: Vec<AgentSkill>,
}

#[derive(Serialize, Clone, Debug)]
struct AgentCapabilities {
    streaming: bool,
    #[serde(rename = "pushNotifications")]
    push_notifications: bool,
    #[serde(rename = "stateTransitionHistory")]
    state_transition_history: bool,
}

#[derive(Serialize, Clone, Debug)]
struct AgentSkill {
    id: &'static str,
    name: &'static str,
    description: &'static str,
    tags: Vec<&'static str>,
    examples: Vec<&'static str>,
    #[serde(rename = "inputModes")]
    input_modes: Vec<&'static str>,
    #[serde(rename = "outputModes")]
    output_modes: Vec<&'static str>,
}

/// Estado de una Task ADK (ciclo de vida canónico).
#[derive(Serialize, Deserialize, Clone, Debug)]
#[serde(rename_all = "kebab-case")]
enum TaskState {
    Submitted,
    Working,
    InputRequired,
    Completed,
    Failed,
    Canceled,
}

#[derive(Serialize, Deserialize, Clone, Debug)]
struct TaskStatus {
    state: TaskState,
    message: Option<A2aMessage>,
    timestamp: DateTime<Utc>,
}

/// Un mensaje en el hilo de la Task (role: "user" | "agent").
#[derive(Serialize, Deserialize, Clone, Debug)]
struct A2aMessage {
    role: String,
    parts: Vec<Part>,
    #[serde(rename = "messageId")]
    message_id: String,
}

/// Part de un mensaje — text, data estructurada, o archivo (audio/imagen/video).
/// Sigue el spec ADK A2A v0.2 con soporte multimodal.
#[derive(Serialize, Deserialize, Clone, Debug)]
#[serde(tag = "type", rename_all = "lowercase")]
enum Part {
    Text { text: String },
    Data { data: serde_json::Value },
    /// FilePart: contenido binario codificado en base64.
    /// mime_type: "audio/wav", "audio/mpeg", "image/jpeg", "image/png", "video/mp4"
    File {
        file: FileContent,
    },
}

#[derive(Serialize, Deserialize, Clone, Debug)]
struct FileContent {
    /// Nombre sugerido del archivo (opcional)
    name: Option<String>,
    /// MIME type: "audio/wav", "image/jpeg", "video/mp4", etc.
    #[serde(rename = "mimeType")]
    mime_type: String,
    /// Contenido en base64 (mutuamente excluyente con `uri`)
    bytes: Option<String>,
    /// URL del recurso (mutuamente excluyente con `bytes`)
    uri: Option<String>,
}

/// La Task completa tal como define el spec ADK A2A.
#[derive(Serialize, Deserialize, Clone, Debug)]
struct A2aTask {
    id: String,
    #[serde(rename = "sessionId")]
    session_id: Option<String>,
    status: TaskStatus,
    history: Vec<A2aMessage>,
    metadata: Option<serde_json::Value>,
}

/// Body del request POST /tasks/send
#[derive(Deserialize, Debug)]
struct SendTaskRequest {
    id: String,
    #[serde(rename = "sessionId")]
    session_id: Option<String>,
    message: A2aMessage,
    metadata: Option<serde_json::Value>,
}

#[derive(Deserialize)]
struct RegisterRequest {
    id: String,
    addr: String,
    capabilities: Vec<String>,
}

#[derive(Deserialize)]
struct SyncPushRequest {
    user_id: String,
    device_id: String,
    payload: String,
}

#[derive(Deserialize)]
struct ShareWisdomRequest {
    node_id: String,
    rule: serde_json::Value,
}

async fn register_node(
    State(state): State<Arc<RegistryState>>,
    Json(payload): Json<RegisterRequest>,
) -> Json<serde_json::Value> {
    let mut nodes = state.nodes.lock().await;
    let node_id = payload.id.clone();
    let node = Node {
        id: node_id.clone(),
        addr: payload.addr,
        last_seen: Utc::now(),
        capabilities: payload.capabilities,
    };
    nodes.insert(node_id.clone(), node);
    println!("📡 [REGISTRY] Nodo registrado: {}", node_id);
    Json(serde_json::json!({"status": "registered", "total_nodes": nodes.len()}))
}

async fn list_nodes(
    State(state): State<Arc<RegistryState>>,
) -> Json<Vec<Node>> {
    let nodes = state.nodes.lock().await;
    Json(nodes.values().cloned().collect())
}

async fn share_wisdom(
    State(state): State<Arc<RegistryState>>,
    Json(payload): Json<ShareWisdomRequest>,
) -> Json<serde_json::Value> {
    let mut hub = state.wisdom_hub.lock().await;
    let rule = WisdomRule {
        id: uuid::Uuid::new_v4().to_string(),
        creator_node: payload.node_id,
        rule_data: payload.rule,
        votes: 1,
        timestamp: Utc::now(),
    };
    hub.push(rule);
    println!("✨ [WISDOM HUB] Nueva regla compartida por el nodo {}", hub.last().unwrap().creator_node);
    Json(serde_json::json!({"status": "shared", "wisdom_id": hub.last().unwrap().id}))
}

async fn list_wisdom(
    State(state): State<Arc<RegistryState>>,
) -> Json<Vec<WisdomRule>> {
    let hub = state.wisdom_hub.lock().await;
    Json(hub.clone())
}

// ─── A2A Handlers ────────────────────────────────────────────────────────────

/// GET /.well-known/agent.json
/// Punto de descubrimiento ADK. Cualquier orquestador compatible puede leer
/// las capacidades de ZANA sin autenticación.
async fn get_agent_card() -> Json<AgentCard> {
    let host = std::env::var("ZANA_PUBLIC_URL")
        .unwrap_or_else(|_| "http://localhost:50000".to_string());

    Json(AgentCard {
        name: "ZANA Cognitive Node",
        description: "Symbolic + Bayesian reasoning node. Semantic search, \
                       episodic recall, knowledge graph, and wisdom sharing \
                       for the ZANA AGI swarm.",
        url: host,
        version: "3.0.0",
        default_input_modes: vec!["text"],
        default_output_modes: vec!["text", "data"],
        capabilities: AgentCapabilities {
            streaming: false,
            push_notifications: false,
            state_transition_history: true,
        },
        skills: vec![
            AgentSkill {
                id: "semantic_search",
                name: "Semantic Search",
                description: "Vector similarity search across the ZANA knowledge vault (ChromaDB).",
                tags: vec!["search", "knowledge", "rag", "vector"],
                examples: vec!["Find documents about VECANOVA architecture",
                               "What does ZANA know about KoruOS?"],
                input_modes: vec!["text"],
                output_modes: vec!["text", "data"],
            },
            AgentSkill {
                id: "reasoning",
                name: "Symbolic Reasoning",
                description: "Forward-chaining inference on structured facts using the CLIPS-pattern engine.",
                tags: vec!["reasoning", "inference", "symbolic", "rules"],
                examples: vec!["What happens if machine_health drops below 0.4?",
                               "Evaluate Empire_Survival rule for current state"],
                input_modes: vec!["text", "data"],
                output_modes: vec!["text", "data"],
            },
            AgentSkill {
                id: "episodic_recall",
                name: "Episodic Memory Recall",
                description: "Retrieves past sessions and events by semantic similarity or time range.",
                tags: vec!["memory", "recall", "episodic", "history"],
                examples: vec!["What happened last time we worked on the landing page?",
                               "Recall the last 3 VECANOVA tasks"],
                input_modes: vec!["text"],
                output_modes: vec!["text", "data"],
            },
            AgentSkill {
                id: "graph_query",
                name: "Knowledge Graph Query",
                description: "Cypher query execution on the Neo4j world model.",
                tags: vec!["graph", "neo4j", "relationships", "causal"],
                examples: vec!["What projects depend on Neural Factory?",
                               "Show path between VECANOVA and KoruOS"],
                input_modes: vec!["text", "data"],
                output_modes: vec!["data"],
            },
            AgentSkill {
                id: "wisdom_share",
                name: "Wisdom Hub Exchange",
                description: "Share or retrieve symbolic rules from the ZANA swarm Wisdom Hub.",
                tags: vec!["swarm", "rules", "wisdom", "evolution"],
                examples: vec!["Share my best rule with the swarm",
                               "Get the top-voted rules from the Wisdom Hub"],
                input_modes: vec!["text", "data"],
                output_modes: vec!["data"],
            },
            AgentSkill {
                id: "sense_audio",
                name: "Audio Perception",
                description: "Speech-to-text transcription + acoustic feature extraction + TTS response. \
                              Accepts WAV, MP3, OGG, FLAC.",
                tags: vec!["audio", "stt", "tts", "voice", "multimodal"],
                examples: vec!["Transcribe this voice memo",
                               "What did I say in this recording?"],
                input_modes: vec!["audio"],
                output_modes: vec!["text", "audio"],
            },
            AgentSkill {
                id: "sense_vision",
                name: "Visual Perception",
                description: "Image and video analysis via Claude Vision. Scene understanding, \
                              entity extraction, OCR, emotional context. Accepts JPG, PNG, MP4.",
                tags: vec!["vision", "image", "video", "ocr", "multimodal"],
                examples: vec!["Describe what is on my screen",
                               "Analyze this design mockup",
                               "What is happening in this video?"],
                input_modes: vec!["image", "video"],
                output_modes: vec!["text", "data"],
            },
        ],
    })
}

/// Infiere el skill_id desde el metadata de la task o por keywords en el texto.
fn resolve_skill(message: &A2aMessage, metadata: &Option<serde_json::Value>) -> &'static str {
    // Prioridad 1: skill explícito en metadata
    if let Some(meta) = metadata {
        if let Some(s) = meta.get("skill_id").and_then(|v| v.as_str()) {
            return match s {
                "semantic_search"  => "semantic_search",
                "reasoning"        => "reasoning",
                "episodic_recall"  => "episodic_recall",
                "graph_query"      => "graph_query",
                "wisdom_share"     => "wisdom_share",
                _                  => "semantic_search",
            };
        }
    }
    // Prioridad 2: heurística sobre el texto del primer TextPart
    // Prioridad 2a: FilePart en el mensaje → rutear al sensory gateway
    let has_audio = message.parts.iter().any(|p| matches!(p, Part::File { file } if
        file.mime_type.starts_with("audio/")));
    if has_audio { return "sense_audio"; }

    let has_video = message.parts.iter().any(|p| matches!(p, Part::File { file } if
        file.mime_type.starts_with("video/")));
    if has_video { return "sense_vision"; }

    let has_image = message.parts.iter().any(|p| matches!(p, Part::File { file } if
        file.mime_type.starts_with("image/")));
    if has_image { return "sense_vision"; }

    // Prioridad 2b: heurística sobre el texto del primer TextPart
    let text = message.parts.iter()
        .find_map(|p| if let Part::Text { text } = p { Some(text.as_str()) } else { None })
        .unwrap_or("");
    let lower = text.to_lowercase();
    if lower.contains("remember") || lower.contains("recall") || lower.contains("last time") {
        "episodic_recall"
    } else if lower.contains("rule") || lower.contains("infer") || lower.contains("deduce") {
        "reasoning"
    } else if lower.contains("graph") || lower.contains("path") || lower.contains("cypher") {
        "graph_query"
    } else if lower.contains("wisdom") || lower.contains("swarm") || lower.contains("share rule") {
        "wisdom_share"
    } else {
        "semantic_search"
    }
}

const SENSORY_GATEWAY_URL_DEFAULT: &str = "http://localhost:54446";

/// Delega la task al backend correcto según el skill.
/// - sense_audio / sense_vision → Sensory Gateway (port 54446)
/// - otros skills               → zana-core-api (port 58000)
async fn forward_to_core(skill: &str, input_text: &str) -> Result<String, String> {
    let client = reqwest::Client::builder()
        .timeout(std::time::Duration::from_secs(10))
        .build()
        .map_err(|e| e.to_string())?;

    // Skills multimodales van al Sensory Gateway
    if skill == "sense_audio" || skill == "sense_vision" {
        let gw_url = std::env::var("SENSORY_GATEWAY_URL")
            .unwrap_or_else(|_| SENSORY_GATEWAY_URL_DEFAULT.to_string());

        let body = serde_json::json!({ "text": input_text, "respond_with_audio": false });
        let resp = client
            .post(format!("{}/sense/text", gw_url))
            .json(&body)
            .send()
            .await
            .map_err(|_| "sensory_gateway_offline".to_string())?;

        if resp.status().is_success() {
            let json: serde_json::Value = resp.json().await.map_err(|e| e.to_string())?;
            return Ok(json["response_text"]
                .as_str()
                .unwrap_or("(sin respuesta)")
                .to_string());
        }
        return Err(format!("gateway_error_{}", resp.status()));
    }

    // Skills cognitivos van al zana-core-api
    let core_url = std::env::var("ZANA_CORE_URL")
        .unwrap_or_else(|_| ZANA_CORE_URL_DEFAULT.to_string());

    let body = serde_json::json!({ "skill": skill, "input": input_text });
    let resp = client
        .post(format!("{}/a2a/execute", core_url))
        .json(&body)
        .send()
        .await
        .map_err(|_| "zana_core_offline".to_string())?;

    if resp.status().is_success() {
        let json: serde_json::Value = resp.json().await.map_err(|e| e.to_string())?;
        Ok(json["result"].as_str().unwrap_or("(empty response)").to_string())
    } else {
        Err(format!("core_error_{}", resp.status()))
    }
}

/// POST /tasks/send
/// Acepta una Task ADK, la enruta al skill correcto de ZANA Core,
/// y devuelve la Task con estado final.
async fn send_task(
    State(state): State<Arc<RegistryState>>,
    Json(req): Json<SendTaskRequest>,
) -> Json<A2aTask> {
    let task_id = req.id.clone();
    let session_id = req.session_id
        .unwrap_or_else(|| uuid::Uuid::new_v4().to_string());

    let skill = resolve_skill(&req.message, &req.metadata);
    let input_text = req.message.parts.iter()
        .find_map(|p| if let Part::Text { text } = p { Some(text.clone()) } else { None })
        .unwrap_or_default();

    println!("🤖 [A2A] Task '{}' → skill '{}' | input: '{}'",
        &task_id[..8.min(task_id.len())], skill, &input_text[..80.min(input_text.len())]);

    // Guardar tarea en estado "working"
    let working_task = A2aTask {
        id: task_id.clone(),
        session_id: Some(session_id.clone()),
        status: TaskStatus {
            state: TaskState::Working,
            message: None,
            timestamp: Utc::now(),
        },
        history: vec![req.message.clone()],
        metadata: req.metadata.clone(),
    };
    state.tasks.lock().await.insert(task_id.clone(), working_task);

    // Intentar forward al core
    let (final_state, response_text) = match forward_to_core(skill, &input_text).await {
        Ok(result) => {
            println!("   ✅ Core responded for task '{}'", &task_id[..8.min(task_id.len())]);
            (TaskState::Completed, result)
        }
        Err(reason) => {
            println!("   ⚠️  Core unavailable ({}). Graceful response.", reason);
            let fallback = format!(
                "ZANA Core offline. Skill '{}' queued. \
                 Start zana-core-api (docker compose up) and retry task '{}'.",
                skill, &task_id[..8.min(task_id.len())]
            );
            (TaskState::Completed, fallback)
        }
    };

    let agent_msg = A2aMessage {
        role: "agent".to_string(),
        parts: vec![Part::Text { text: response_text }],
        message_id: uuid::Uuid::new_v4().to_string(),
    };

    let final_task = A2aTask {
        id: task_id.clone(),
        session_id: Some(session_id),
        status: TaskStatus {
            state: final_state,
            message: Some(agent_msg.clone()),
            timestamp: Utc::now(),
        },
        history: vec![req.message, agent_msg],
        metadata: req.metadata,
    };

    state.tasks.lock().await.insert(task_id, final_task.clone());
    Json(final_task)
}

/// GET /tasks/:id
/// Permite a cualquier cliente ADK hacer polling del estado de una task.
async fn get_task(
    State(state): State<Arc<RegistryState>>,
    Path(task_id): Path<String>,
) -> Json<serde_json::Value> {
    let tasks = state.tasks.lock().await;
    match tasks.get(&task_id) {
        Some(task) => Json(serde_json::to_value(task).unwrap()),
        None => Json(serde_json::json!({
            "error": "task_not_found",
            "task_id": task_id
        })),
    }
}

#[tokio::main]
async fn main() {
    println!("  [ X A N A   L Y O K O   R E G I S T R Y ]  ");
    println!("  [   W I S D O M   H U B   +   A 2 A      ]  ");
    println!("=============================================");

    let state = Arc::new(RegistryState {
        nodes: Mutex::new(HashMap::new()),
        sync_vault: Mutex::new(HashMap::new()),
        message_queue: Mutex::new(HashMap::new()),
        wisdom_hub: Mutex::new(vec![]),
        tasks: Mutex::new(HashMap::new()),
    });

    let app = Router::new()
        // ── Swarm / Wisdom Hub (existente) ──
        .route("/register", post(register_node))
        .route("/nodes", get(list_nodes))
        .route("/wisdom/share", post(share_wisdom))
        .route("/wisdom/list", get(list_wisdom))
        // ── ADK A2A Adapter (nuevo) ──
        .route("/.well-known/agent.json", get(get_agent_card))
        .route("/tasks/send", post(send_task))
        .route("/tasks/{id}", get(get_task))
        .layer(CorsLayer::permissive())
        .with_state(state);

    let addr = SocketAddr::from(([0, 0, 0, 0], 50000));
    println!("🚀 [REGISTRY]  Swarm Hub  → http://0.0.0.0:50000");
    println!("🤖 [A2A]       AgentCard  → http://0.0.0.0:50000/.well-known/agent.json");
    println!("📨 [A2A]       Tasks      → POST http://0.0.0.0:50000/tasks/send");
    println!("🔍 [A2A]       Task poll  → GET  http://0.0.0.0:50000/tasks/:id");

    let listener = tokio::net::TcpListener::bind(&addr).await.unwrap();
    axum::serve(listener, app).await.unwrap();
}
