use serde::Serialize;
use tauri::State;
use crate::AppState;

#[derive(Serialize)]
pub struct GatewayStatus {
    pub running: bool,
    pub port: u16,
    pub url: String,
}

#[tauri::command]
pub async fn gateway_status(state: State<'_, AppState>) -> Result<GatewayStatus, String> {
    let alive = state.gateway.is_alive().await;
    Ok(GatewayStatus {
        running: alive,
        port: state.gateway.port,
        url: format!("http://localhost:{}", state.gateway.port),
    })
}

#[tauri::command]
pub async fn restart_gateway(state: State<'_, AppState>) -> Result<(), String> {
    state.gateway.stop().await;
    let bin = state.gateway_bin.clone();
    state.gateway.start(bin).await.map_err(|e| e.to_string())?;
    state.gateway.wait_ready(15).await;
    Ok(())
}

#[tauri::command]
pub fn app_version() -> &'static str {
    env!("CARGO_PKG_VERSION")
}
