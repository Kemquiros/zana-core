use tauri::{
    menu::{Menu, MenuItem},
    tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent},
    AppHandle, Manager,
};

pub fn build(app: &AppHandle) -> tauri::Result<()> {
    let show    = MenuItem::with_id(app, "show",    "Abrir ZANA",          true,  None::<&str>)?;
    let status  = MenuItem::with_id(app, "status",  "Gateway: iniciando…", false, None::<&str>)?;
    let restart = MenuItem::with_id(app, "restart", "Reiniciar gateway",   true,  None::<&str>)?;
    let sep     = tauri::menu::PredefinedMenuItem::separator(app)?;
    let quit    = MenuItem::with_id(app, "quit",    "Salir",               true,  None::<&str>)?;

    let menu = Menu::with_items(app, &[&show, &status, &restart, &sep, &quit])?;

    TrayIconBuilder::with_id("zana-tray")
        .menu(&menu)
        .on_menu_event(|app, event| match event.id.as_ref() {
            "show"    => toggle_window(app),
            "restart" => {
                let handle = app.clone();
                tauri::async_runtime::spawn(async move {
                    if let Some(state) = handle.try_state::<crate::AppState>() {
                        let bin = state.gateway_bin.clone();
                        state.gateway.stop().await;
                        let _ = state.gateway.start(bin).await;
                        state.gateway.wait_ready(15).await;
                    }
                });
            }
            "quit" => app.exit(0),
            _ => {}
        })
        .on_tray_icon_event(|tray, event| {
            if let TrayIconEvent::Click {
                button: MouseButton::Left,
                button_state: MouseButtonState::Up,
                ..
            } = event
            {
                toggle_window(tray.app_handle());
            }
        })
        .build(app)?;

    Ok(())
}

fn toggle_window(app: &AppHandle) {
    if let Some(win) = app.get_webview_window("main") {
        if win.is_visible().unwrap_or(false) {
            let _ = win.hide();
        } else {
            let _ = win.show();
            let _ = win.set_focus();
        }
    }
}

pub fn update_status(app: &AppHandle, running: bool) {
    if let Some(tray) = app.tray_by_id("zana-tray") {
        let label = if running { "Gateway: activo ✓" } else { "Gateway: detenido ✗" };
        // Rebuild the menu with updated status label
        if let Ok(status) = MenuItem::with_id(app, "status", label, false, None::<&str>) {
            if let (Ok(show), Ok(restart), Ok(sep), Ok(quit)) = (
                MenuItem::with_id(app, "show",    "Abrir ZANA",        true,  None::<&str>),
                MenuItem::with_id(app, "restart", "Reiniciar gateway", true,  None::<&str>),
                tauri::menu::PredefinedMenuItem::separator(app),
                MenuItem::with_id(app, "quit",    "Salir",             true,  None::<&str>),
            ) {
                if let Ok(menu) = Menu::with_items(app, &[&show, &status, &restart, &sep, &quit]) {
                    let _ = tray.set_menu(Some(menu));
                }
            }
        }
    }
}
