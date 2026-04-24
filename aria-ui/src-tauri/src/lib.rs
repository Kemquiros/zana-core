mod commands;
mod daemon;
mod tray;

use std::path::PathBuf;
use std::sync::Arc;
use tauri::{Manager, RunEvent};
use daemon::{data_dir, init_sqlite, Gateway};

pub struct AppState {
    pub gateway: Arc<Gateway>,
    pub gateway_bin: PathBuf,
}

pub fn run() {
    env_logger::init();
    log::info!("Iniciando Córtex ZANA...");

    tauri::Builder::default()
        .plugin(tauri_plugin_single_instance::init(|app, _args, _cwd| {
            if let Some(win) = app.get_webview_window("main") {
                let _ = win.show();
                let _ = win.set_focus();
            }
        }))
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_process::init())
        .plugin(tauri_plugin_notification::init())
        .setup(|app| {
            // 1. Mostrar ventana de inmediato
            if let Some(win) = app.get_webview_window("main") {
                log::info!("Desplegando ventana principal...");
                let _ = win.show().ok();
            }

            // 2. Resolver ruta del gateway (Sidecar)
            let mut gateway_bin = PathBuf::new();
            
            // Caso A: Instalación global Debian (/usr/bin)
            let global_bin = PathBuf::from("/usr/bin/zana-gateway");
            if global_bin.exists() { 
                gateway_bin = global_bin; 
            } else {
                // Caso B: Carpeta de recursos de la aplicación
                if let Ok(res_dir) = app.path().resource_dir() {
                    let res_bin = res_dir.join("zana-gateway");
                    if res_bin.exists() { 
                        gateway_bin = res_bin; 
                    } else {
                        // Caso C: Ruta de desarrollo (sidecar folder)
                        let dev_bin = res_dir.join("_up_").join("sidecar").join("zana-gateway");
                        if dev_bin.exists() { gateway_bin = dev_bin; }
                    }
                }
            }
            
            log::info!("Binario Gateway detectado: {}", gateway_bin.display());

            // 3. Inicializar base de datos local
            let db_path = data_dir().join("zana.db");
            let _ = init_sqlite(&db_path);

            // 4. Registrar estado global
            let gateway_port: u16 = std::env::var("ZANA_GATEWAY_PORT")
                .ok()
                .and_then(|v| v.parse().ok())
                .unwrap_or(54446);
            let gateway = Arc::new(Gateway::new(gateway_port));
            
            app.manage(AppState { 
                gateway: gateway.clone(),
                gateway_bin: gateway_bin.clone(),
            });

            // 5. Configurar bandeja de sistema
            let _ = tray::build(app.handle());

            // 6. Lanzar Gateway en segundo plano
            let handle = app.handle().clone();
            tauri::async_runtime::spawn(async move {
                if gateway_bin.as_os_str().is_empty() {
                    log::warn!("Aviso: No se encontró el binario del gateway.");
                    return;
                }

                log::info!("Iniciando Gateway Sensorial en puerto {}...", gateway_port);
                if let Err(e) = gateway.start(gateway_bin).await {
                    log::error!("Error crítico al lanzar gateway: {}", e);
                } else {
                    let ready = gateway.wait_ready(15).await;
                    log::info!("Estado del Gateway: {}", if ready { "EN LÍNEA" } else { "TIMEOUT" });
                    tray::update_status(&handle, ready);
                }
            });

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            commands::gateway_status,
            commands::restart_gateway,
            commands::app_version,
            commands::check_onboarding_status,
            commands::save_env_config,
        ])
        .build(tauri::generate_context!())
        .expect("error building tauri app")
        .run(|app, event| {
            if let RunEvent::ExitRequested { api, .. } = event {
                api.prevent_exit();
                if let Some(win) = app.get_webview_window("main") {
                    let _ = win.hide();
                }
            }
        });
}
