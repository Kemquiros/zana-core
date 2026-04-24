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
            // En producción (Debian), Tauri coloca los recursos en /usr/lib/ZANA/
            let res_dir = app.path().resource_dir().unwrap_or_else(|_| PathBuf::from("."));
            
            // Nombre del binario según tauri.conf.json (externalBin)
            // Tauri añade el triple automáticamente al empaquetar, pero aquí 
            // intentamos una ruta genérica que funcione en dev y prod.
            let gateway_bin = res_dir.join("zana-gateway");
            
            log::info!("Ruta base de recursos: {}", res_dir.display());

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
                log::info!("Iniciando Gateway Sensorial en puerto {}...", gateway_port);
                // Intentar lanzar el gateway. Si falla, la app sigue funcionando (modo UI only)
                if let Err(e) = gateway.start(gateway_bin).await {
                    log::warn!("Aviso: No se pudo iniciar el gateway sidecar: {}", e);
                } else {
                    let ready = gateway.wait_ready(10).await;
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
