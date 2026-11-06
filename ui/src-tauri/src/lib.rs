use tauri::{
    menu::{Menu, MenuItem, PredefinedMenuItem},
    tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent},
    Manager,
};

#[tauri::command]
fn get_session_token() -> Result<String, String> {
    let local_app_data = std::env::var("LOCALAPPDATA").unwrap_or_else(|_| ".".into());
    let token_path = std::path::PathBuf::from(local_app_data)
        .join("Jarvis")
        .join("session.token");

    if token_path.is_file() {
        std::fs::read_to_string(&token_path)
            .map(|s| s.trim().to_string())
            .map_err(|e| format!("Failed to read session token: {e}"))
    } else {
        // Fallback for dev mode when backend writes token locally
        let fallback_path = std::path::PathBuf::from("session.token");
        if fallback_path.is_file() {
            std::fs::read_to_string(&fallback_path)
                .map(|s| s.trim().to_string())
                .map_err(|e| format!("Failed to read session token: {e}"))
        } else {
            Err("Session token file not found".into())
        }
    }
}

fn request_backend_shutdown() {
    let token = get_session_token().unwrap_or_default();
    let auth_header = if !token.is_empty() {
        format!("Authorization: Bearer {}\r\nX-Session-Token: {}\r\n", token, token)
    } else {
        String::new()
    };

    if let Ok(mut stream) = std::net::TcpStream::connect("127.0.0.1:8765") {
        let _ = stream.set_write_timeout(Some(std::time::Duration::from_millis(1500)));
        let _ = stream.set_read_timeout(Some(std::time::Duration::from_millis(1500)));
        let req = format!(
            "POST /api/shutdown HTTP/1.1\r\nHost: 127.0.0.1:8765\r\n{}Content-Length: 0\r\nConnection: close\r\n\r\n",
            auth_header
        );
        use std::io::{Read, Write};
        let _ = stream.write_all(req.as_bytes());
        let _ = stream.flush();
        let mut buf = [0u8; 512];
        let _ = stream.read(&mut buf);
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .setup(|app| {
            if cfg!(debug_assertions) {
                app.handle().plugin(
                    tauri_plugin_log::Builder::default()
                        .level(log::LevelFilter::Info)
                        .build(),
                )?;
            }

            let show_item = MenuItem::with_id(app, "show", "Показать Kirieshka", true, None::<&str>)?;
            let hide_item = MenuItem::with_id(app, "hide", "Скрыть в трей", true, None::<&str>)?;
            let separator = PredefinedMenuItem::separator(app)?;
            let quit_item = MenuItem::with_id(app, "quit", "Выход", true, None::<&str>)?;

            let menu = Menu::with_items(app, &[&show_item, &hide_item, &separator, &quit_item])?;

            let mut tray_builder = TrayIconBuilder::new()
                .menu(&menu)
                .show_menu_on_left_click(false)
                .on_menu_event(|app, event| match event.id.as_ref() {
                    "show" => {
                        if let Some(window) = app.get_webview_window("main") {
                            let _ = window.show();
                            let _ = window.unminimize();
                            let _ = window.set_focus();
                        }
                    }
                    "hide" => {
                        if let Some(window) = app.get_webview_window("main") {
                            let _ = window.hide();
                        }
                    }
                    "quit" => {
                        request_backend_shutdown();
                        std::thread::sleep(std::time::Duration::from_millis(300));
                        app.exit(0);
                    }
                    _ => {}
                })
                .on_tray_icon_event(|tray, event| {
                    if let TrayIconEvent::Click {
                        button: MouseButton::Left,
                        button_state: MouseButtonState::Up,
                        ..
                    } = event
                    {
                        let app = tray.app_handle();
                        if let Some(window) = app.get_webview_window("main") {
                            if window.is_visible().unwrap_or(false) {
                                let _ = window.hide();
                            } else {
                                let _ = window.show();
                                let _ = window.unminimize();
                                let _ = window.set_focus();
                            }
                        }
                    }
                });

            if let Some(icon) = app.default_window_icon() {
                tray_builder = tray_builder.icon(icon.clone());
            }

            let _tray = tray_builder.build(app)?;

            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { api, .. } = event {
                api.prevent_close();
                let _ = window.hide();
            }
        })
        .invoke_handler(tauri::generate_handler![get_session_token])
        .run(tauri::generate_context!())
        .expect("error while building tauri application");
}
