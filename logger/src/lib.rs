use serde::{Serialize, Deserialize};
use std::fs::{OpenOptions, File};
use std::io::{Write, BufWriter};
use std::path::PathBuf;
use chrono::Local;

#[derive(Debug, Clone, Copy, Serialize, Deserialize)]
pub enum LogMode {
    Total,
    Rotary(u64), // Max size in bytes
    LayeredGlacier,
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq, Hash)]
pub enum LogLevel {
    Raw = 0,       // Sensorial raw capture
    Cognitive = 1, // Kalman/Surprise decisions
    Evolution = 2, // IDLE-Zero combats
    Network = 3,   // A2A Handshakes
}

pub struct SovereignLogger {
    pub mode: LogMode,
    pub storage_path: PathBuf,
}

impl SovereignLogger {
    pub fn new(mode: LogMode, path: &str) -> Self {
        let storage_path = PathBuf::from(path);
        std::fs::create_dir_all(&storage_path).ok();
        Self { mode, storage_path }
    }

    pub fn log(&self, mode: LogMode, level: LogLevel, tag: &str, message: &str) {
        let timestamp = Local::now().format("%Y-%m-%d %H:%M:%S%.3f");
        let log_line = format!("[{}] [LEVEL:{:?}] [{}] {}\n", timestamp, level, tag, message);

        match mode {
            LogMode::Total => self.write_to_file("total.log", &log_line),
            LogMode::Rotary(max_size) => self.write_rotary("active.log", &log_line, max_size),
            LogMode::LayeredGlacier => self.write_layered(level, &log_line),
        }
    }

    fn write_to_file(&self, filename: &str, content: &str) {
        let path = self.storage_path.join(filename);
        if let Ok(mut file) = OpenOptions::new().create(true).append(true).open(&path) {
            let _ = file.write_all(content.as_bytes());
        }
    }

    fn write_rotary(&self, filename: &str, content: &str, max_size: u64) {
        let path = self.storage_path.join(filename);
        if let Ok(metadata) = std::fs::metadata(&path) {
            if metadata.len() > max_size {
                let mut old_path = path.clone();
                old_path.set_extension("old");
                std::fs::rename(&path, &old_path).ok();
            }
        }
        self.write_to_file(filename, content);
    }

    fn write_layered(&self, level: LogLevel, content: &str) {
        let filename = match level {
            LogLevel::Raw => "raw_sense.log",
            LogLevel::Cognitive => "cognitive_cortex.log",
            LogLevel::Evolution => "evolutionary_idle.log",
            LogLevel::Network => "network.log",
        };
        self.write_to_file(filename, content);
    }

    pub async fn offload_to_glacier(&self) -> Result<(), String> {
        println!("❄️ [ZANA GLACIER] Starting cold memory archival...");

        // Scan for heavy or layer-specific log files
        let layers = ["raw_sense.log", "cognitive_cortex.log", "evolutionary_idle.log", "network.log"];
        
        for layer in layers {
            let path = self.storage_path.join(layer);
            if path.exists() {
                println!("📦 [Glacier] Comprimiendo capa: {}", layer);
                // Aquí iría la lógica de compresión (gzip/zstd) y cifrado GCM-256
                
                println!("🚀 [Glacier] Trasladando a servidores de VECANOVA (Simulado)...");
                // Simulación de delay de red
                tokio::time::sleep(tokio::time::Duration::from_millis(500)).await;
                
                // Una vez trasladado, el archivo local se limpia o se borra
                // std::fs::remove_file(&path).ok();
            }
        }
        
        println!("✅ [Glacier] Sincronización de memoria fría completada.");
        Ok(())
    }
}
