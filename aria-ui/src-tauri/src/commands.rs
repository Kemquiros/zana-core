use serde::Serialize;
use tauri::State;
use crate::AppState;
use std::fs;
use std::path::PathBuf;

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

#[tauri::command]
pub fn check_onboarding_status() -> Result<bool, String> {
    let home = dirs::home_dir().ok_or("No home directory found")?;
    let zana_dir = home.join(".config").join("zana");
    let onboarded_file = zana_dir.join(".onboarded");
    Ok(onboarded_file.exists())
}

#[tauri::command]
pub fn save_env_config(config: std::collections::HashMap<String, String>) -> Result<(), String> {
    let home = dirs::home_dir().ok_or("No home directory found")?;
    let zana_dir = home.join(".zana");
    
    // Create ~/.zana if it doesn't exist
    if !zana_dir.exists() {
        fs::create_dir_all(&zana_dir).map_err(|e| e.to_string())?;
    }
    
    let env_file = zana_dir.join(".env");
    let mut env_content = String::new();
    
    if env_file.exists() {
        env_content = fs::read_to_string(&env_file).unwrap_or_default();
    }
    
    let mut new_lines: Vec<String> = Vec::new();
    let mut written_keys = std::collections::HashSet::new();
    
    for line in env_content.lines() {
        if line.contains('=') && !line.trim_start().starts_with('#') {
            let parts: Vec<&str> = line.splitn(2, '=').collect();
            let key = parts[0].trim().to_string();
            if let Some(val) = config.get(&key) {
                new_lines.push(format!("{}={}", key, val));
                written_keys.insert(key);
                continue;
            }
        }
        new_lines.push(line.to_string());
    }
    
    for (k, v) in &config {
        if !written_keys.contains(k) {
            new_lines.push(format!("{}={}", k, v));
        }
    }
    
    fs::write(&env_file, new_lines.join("\n")).map_err(|e| e.to_string())?;
    
    // Also touch the .onboarded file to mark setup as complete
    let config_dir = home.join(".config").join("zana");
    if !config_dir.exists() {
        fs::create_dir_all(&config_dir).map_err(|e| e.to_string())?;
    }
    fs::write(config_dir.join(".onboarded"), "").map_err(|e| e.to_string())?;
    
    Ok(())
}
