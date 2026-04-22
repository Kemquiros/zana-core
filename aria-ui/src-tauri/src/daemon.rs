use std::path::PathBuf;
use std::time::Duration;
use tokio::process::{Child, Command};
use tokio::sync::Mutex;
use tokio::time::sleep;
use std::sync::Arc;

pub struct Gateway {
    child: Arc<Mutex<Option<Child>>>,
    pub port: u16,
}

impl Gateway {
    pub fn new(port: u16) -> Self {
        Self { child: Arc::new(Mutex::new(None)), port }
    }

    pub async fn start(&self, binary: PathBuf) -> anyhow::Result<()> {
        let mut guard = self.child.lock().await;
        if guard.is_some() {
            return Ok(());
        }

        let child = Command::new(&binary)
            .env("ZANA_GATEWAY_PORT", self.port.to_string())
            .env("ZANA_DB_PATH", data_dir().join("zana.db").to_str().unwrap())
            .kill_on_drop(true)
            .spawn()?;

        log::info!("gateway started pid={}", child.id().unwrap_or(0));
        *guard = Some(child);
        Ok(())
    }

    pub async fn stop(&self) {
        let mut guard = self.child.lock().await;
        if let Some(mut child) = guard.take() {
            let _ = child.kill().await;
        }
    }

    pub async fn is_alive(&self) -> bool {
        let url = format!("http://localhost:{}/health", self.port);
        reqwest::get(&url).await.map(|r| r.status().is_success()).unwrap_or(false)
    }

    /// Waits up to `timeout_secs` for the gateway to respond.
    pub async fn wait_ready(&self, timeout_secs: u64) -> bool {
        for _ in 0..(timeout_secs * 2) {
            if self.is_alive().await {
                return true;
            }
            sleep(Duration::from_millis(500)).await;
        }
        false
    }
}

pub fn data_dir() -> PathBuf {
    dirs::data_local_dir()
        .unwrap_or_else(|| PathBuf::from("."))
        .join("ZANA")
}

pub fn init_sqlite(db_path: &PathBuf) -> rusqlite::Result<()> {
    std::fs::create_dir_all(db_path.parent().unwrap()).ok();
    let conn = rusqlite::Connection::open(db_path)?;
    conn.execute_batch(
        "PRAGMA journal_mode=WAL;
         CREATE TABLE IF NOT EXISTS sessions (
             id    TEXT PRIMARY KEY,
             ts    INTEGER NOT NULL,
             title TEXT
         );
         CREATE TABLE IF NOT EXISTS messages (
             id         TEXT PRIMARY KEY,
             session_id TEXT NOT NULL REFERENCES sessions(id),
             role       TEXT NOT NULL,
             text       TEXT NOT NULL,
             emotion    TEXT,
             surprise   REAL,
             modality   TEXT,
             ts         INTEGER NOT NULL
         );
         CREATE INDEX IF NOT EXISTS msg_session ON messages(session_id, ts);",
    )?;
    log::info!("sqlite ready at {}", db_path.display());
    Ok(())
}
