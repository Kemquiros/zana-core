mod commands;
mod daemon;
mod tray;

use std::path::PathBuf;
use tauri::{Manager, RunEvent};
use daemon::{data_dir, init_sqlite, Gateway};

pub struct AppState {
    pub gateway: Gateway,
    pub gateway_bin: PathBuf,
}

pub fn run() {
    env_logger::init();

    tauri::Builder::default()
        .plugin(tauri_plugin_single_instance::init(|app, _args, _cwd| {
            if let Some(win) = app.get_webview_window("main") {
                let _ = win.show();
                let _ = win.set_focus();
            }
        }))
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_autostart::init(
            tauri_plugin_autostart::MacosLauncher::LaunchAgent,
            Some(vec!["--minimized"]),
        ))
        .plugin(tauri_plugin_notification::init())
        .setup(|app| {
            // resolve sidecar binary path
            let res = app.path().resource_dir()?;
            let gateway_bin = res.join("zana-gateway");

            // init local SQLite
            let db_path = data_dir().join("zana.db");
            if let Err(e) = init_sqlite(&db_path) {
                log::error!("sqlite init failed: {e}");
            }

            // register app state — port from env, default 54446
            let gateway_port: u16 = std::env::var("ZANA_GATEWAY_PORT")
                .ok()
                .and_then(|v| v.parse().ok())
                .unwrap_or(54446);
            let gateway = Gateway::new(gateway_port);
            app.manage(AppState { gateway, gateway_bin: gateway_bin.clone() });

            // build system tray
            tray::build(app.handle())?;

            // start gateway in background
            let handle = app.handle().clone();
            tauri::async_runtime::spawn(async move {
                let state = handle.state::<AppState>();
                match state.gateway.start(gateway_bin).await {
                    Ok(_) => {
                        let ready = state.gateway.wait_ready(20).await;
                        tray::update_status(&handle, ready);
                        if ready {
                            if let Some(win) = handle.get_webview_window("main") {
                                let _ = win.show();
                            }
                        }
                    }
                    Err(e) => log::warn!("gateway sidecar not available: {e}"),
                }
            });

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            commands::gateway_status,
            commands::restart_gateway,
            commands::app_version,
        ])
        .build(tauri::generate_context!())
        .expect("error building tauri app")
        .run(|app, event| {
            if let RunEvent::ExitRequested { api, .. } = event {
                // keep running in tray on close
                api.prevent_exit();
                if let Some(win) = app.get_webview_window("main") {
                    let _ = win.hide();
                }
            }
        });
}
