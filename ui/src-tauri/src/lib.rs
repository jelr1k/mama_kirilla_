use std::sync::atomic::{AtomicBool, AtomicU32, Ordering};
use tauri::{
    menu::{Menu, MenuItem, PredefinedMenuItem},
    tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent},
    Emitter, LogicalSize, Manager, PhysicalPosition,
};

struct IslandHitState {
    visible: AtomicBool,
    expanded: AtomicBool,
    pill_width: AtomicU32,
    pill_height: AtomicU32,
}

impl Default for IslandHitState {
    fn default() -> Self {
        Self {
            visible: AtomicBool::new(false),
            expanded: AtomicBool::new(false),
            pill_width: AtomicU32::new(232),
            pill_height: AtomicU32::new(40),
        }
    }
}

#[cfg(target_os = "windows")]
fn sync_island_hit_region(_window: &tauri::WebviewWindow, _state: &IslandHitState) {
    // No-op: SetWindowRgn breaks WebView2 DWM alpha transparency on Windows 10/11
    // (producing opaque white jagged corners around the pill). Click-through is
    // handled by spawn_island_hit_watcher instead.
}

#[cfg(not(target_os = "windows"))]
fn sync_island_hit_region(_window: &tauri::WebviewWindow, _state: &IslandHitState) {}

/// The island HWND stays a fixed 720x382 transparent surface (no resizes = no WebView2 jank).
/// Click-through outside the visible pill/panel is toggled here by polling the cursor and
/// flipping ignore_cursor_events only when the cursor crosses the hit-rect boundary.
#[cfg(target_os = "windows")]
fn spawn_island_hit_watcher(app: tauri::AppHandle) {
    #[repr(C)]
    struct Point {
        x: i32,
        y: i32,
    }
    #[repr(C)]
    struct Rect {
        left: i32,
        top: i32,
        right: i32,
        bottom: i32,
    }
    #[link(name = "user32")]
    #[link(name = "user32")]
    unsafe extern "system" {
        fn GetCursorPos(lp_point: *mut Point) -> i32;
        fn GetWindowRect(h_wnd: isize, lp_rect: *mut Rect) -> i32;
        fn GetAsyncKeyState(v_key: i32) -> i16;
    }
    const HIT_PAD: f64 = 8.0;

    std::thread::spawn(move || {
        let mut ignoring: Option<bool> = None;
        loop {
            let state = app.state::<IslandHitState>();
            let window = app.get_webview_window("island");
            let Some(window) = window.filter(|_| state.visible.load(Ordering::Relaxed)) else {
                ignoring = None;
                std::thread::sleep(std::time::Duration::from_millis(150));
                continue;
            };
            let Ok(hwnd) = window.hwnd() else {
                std::thread::sleep(std::time::Duration::from_millis(150));
                continue;
            };

            let mut rect = Rect { left: 0, top: 0, right: 0, bottom: 0 };
            let mut cursor = Point { x: 0, y: 0 };
            let ok = unsafe {
                GetWindowRect(hwnd.0 as isize, &mut rect) != 0 && GetCursorPos(&mut cursor) != 0
            };
            if ok {
                let rect_w = (rect.right - rect.left).max(1);
                let scale = (rect_w as f64 / 720.0).max(0.5);
                let hit_w = ((state.pill_width.load(Ordering::Relaxed) as f64 + HIT_PAD) * scale).round() as i32;
                let hit_h = ((state.pill_height.load(Ordering::Relaxed) as f64 + HIT_PAD) * scale).round() as i32;
                let left = rect.left + (rect_w - hit_w) / 2;
                let inside = cursor.x >= left
                    && cursor.x < left + hit_w
                    && cursor.y >= rect.top
                    && cursor.y < rect.top + hit_h;
                // Keep events while LMB is held after starting inside (drag, text selection).
                let lmb_down = unsafe { GetAsyncKeyState(0x01) } < 0;
                let want_ignore = !inside && !(lmb_down && ignoring == Some(false));
                if ignoring != Some(want_ignore) {
                    let _ = window.set_ignore_cursor_events(want_ignore);
                    ignoring = Some(want_ignore);
                }
            }
            std::thread::sleep(std::time::Duration::from_millis(16));
        }
    });
}

#[cfg(not(target_os = "windows"))]
fn spawn_island_hit_watcher(_app: tauri::AppHandle) {}

#[tauri::command]
fn get_session_token() -> Result<String, String> {
    let local_app_data = std::env::var("LOCALAPPDATA").unwrap_or_else(|_| ".".into());
    let base_dir = std::path::PathBuf::from(local_app_data);
    let primary_token = base_dir.join("Assistant").join("session.token");

    let token_path = if primary_token.is_file() {
        primary_token
    } else {
        std::path::PathBuf::from("session.token")
    };

    if token_path.is_file() {
        std::fs::read_to_string(&token_path)
            .map(|s| s.trim().to_string())
            .map_err(|e| format!("Failed to read session token: {e}"))
    } else {
        Err("Session token file not found".into())
    }
}

#[derive(serde::Serialize)]
#[serde(rename_all = "camelCase")]
struct IslandBoundsResult {
    center_x: i32,
    y: i32,
    docked_top: bool,
    monitor_top: i32,
}

fn find_target_monitor(
    window: &tauri::WebviewWindow,
    anchor_center_x: Option<i32>,
    anchor_y: Option<i32>,
) -> Option<tauri::Monitor> {
    if let (Some(cx), Some(ay)) = (anchor_center_x, anchor_y)
        && let Ok(monitors) = window.available_monitors()
    {
        for m in monitors {
            let p = m.position();
            let s = m.size();
            let right = p.x + s.width as i32;
            let bottom = p.y + s.height as i32;
            if cx >= p.x && cx < right && (ay + 12) >= p.y && (ay + 12) < bottom {
                return Some(m);
            }
        }
    }
    window
        .current_monitor()
        .ok()
        .flatten()
        .or_else(|| window.primary_monitor().ok().flatten())
}

#[cfg(target_os = "windows")]
fn apply_window_bounds_atomic(
    window: &tauri::WebviewWindow,
    x: i32,
    y: i32,
    w: i32,
    h: i32,
) -> bool {
    const SWP_NOZORDER: u32 = 0x0004;
    const SWP_NOACTIVATE: u32 = 0x0010;
    #[link(name = "user32")]
    unsafe extern "system" {
        fn SetWindowPos(
            h_wnd: isize,
            h_wnd_insert_after: isize,
            x: i32,
            y: i32,
            cx: i32,
            cy: i32,
            u_flags: u32,
        ) -> i32;
    }
    if let Ok(hwnd) = window.hwnd() {
        let ok = unsafe {
            SetWindowPos(hwnd.0 as isize, 0, x, y, w, h, SWP_NOZORDER | SWP_NOACTIVATE)
        };
        return ok != 0;
    }
    false
}

#[cfg(not(target_os = "windows"))]
fn apply_window_bounds_atomic(
    window: &tauri::WebviewWindow,
    x: i32,
    y: i32,
    w: i32,
    h: i32,
) -> bool {
    false
}

#[tauri::command]
fn set_island_bounds(
    app: tauri::AppHandle,
    width: f64,
    height: f64,
    anchor_center_x: Option<i32>,
    anchor_y: Option<i32>,
) -> Result<IslandBoundsResult, String> {
    let window = app
        .get_webview_window("island")
        .ok_or_else(|| "Island window not found".to_string())?;

    let w = width.clamp(160.0, 960.0);
    let h = height.clamp(32.0, 640.0);

    if let Some(m) = find_target_monitor(&window, anchor_center_x, anchor_y) {
        let scale = m.scale_factor();
        let m_pos = m.position();
        let m_size = m.size();
        let phys_w = (w * scale).round() as i32;
        let phys_h = (h * scale).round() as i32;

        let desired_center_x = anchor_center_x.unwrap_or_else(|| m_pos.x + (m_size.width as i32) / 2);
        let desired_y = anchor_y.unwrap_or(m_pos.y);

        let raw_x = desired_center_x - phys_w / 2;
        let max_x = m_pos.x + (m_size.width as i32 - phys_w).max(0);
        let max_y = m_pos.y + (m_size.height as i32 - phys_h).max(0);

        let x = raw_x.clamp(m_pos.x, max_x);
        let y = desired_y.clamp(m_pos.y, max_y);

        if !apply_window_bounds_atomic(&window, x, y, phys_w, phys_h) {
            let _ = window.set_size(LogicalSize::new(w, h));
            let _ = window.set_position(PhysicalPosition::new(x, y));
        }

        let docked_top = (y - m_pos.y).abs() <= 8;
        return Ok(IslandBoundsResult {
            center_x: desired_center_x,
            y,
            docked_top,
            monitor_top: m_pos.y,
        });
    }

    let _ = window.set_size(LogicalSize::new(w, h));
    Ok(IslandBoundsResult {
        center_x: anchor_center_x.unwrap_or(0),
        y: anchor_y.unwrap_or(0),
        docked_top: anchor_y.unwrap_or(0) <= 8,
        monitor_top: 0,
    })
}

#[tauri::command]
fn get_island_anchor(app: tauri::AppHandle, snap_top: Option<bool>) -> Result<IslandBoundsResult, String> {
    let window = app
        .get_webview_window("island")
        .ok_or_else(|| "Island window not found".to_string())?;

    let pos = window
        .outer_position()
        .map_err(|e| format!("Failed to read island position: {e}"))?;
    let size = window
        .outer_size()
        .map_err(|e| format!("Failed to read island size: {e}"))?;

    let center_x = pos.x + (size.width as i32) / 2;
    let monitor = find_target_monitor(&window, Some(center_x), Some(pos.y));
    let monitor_top = monitor.as_ref().map(|m| m.position().y).unwrap_or(0);
    let mut y = pos.y;
    let docked_top = (y - monitor_top).abs() <= 10;

    if snap_top.unwrap_or(false) && docked_top && y != monitor_top {
        y = monitor_top;
        let _ = apply_window_bounds_atomic(&window, pos.x, y, size.width as i32, size.height as i32);
    }

    Ok(IslandBoundsResult {
        center_x,
        y,
        docked_top,
        monitor_top,
    })
}

#[tauri::command]
fn get_island_visible(app: tauri::AppHandle) -> bool {
    app.get_webview_window("island")
        .and_then(|w| w.is_visible().ok())
        .unwrap_or(false)
}

#[tauri::command]
fn set_island_visible(
    app: tauri::AppHandle,
    state: tauri::State<'_, IslandHitState>,
    visible: bool,
    anchor_center_x: Option<i32>,
    anchor_y: Option<i32>,
) -> Result<(), String> {
    let window = app
        .get_webview_window("island")
        .ok_or_else(|| "Island window not found".to_string())?;

    if visible {
        state.expanded.store(false, Ordering::Relaxed);
        state.visible.store(true, Ordering::Relaxed);
        let _ = set_island_bounds(app.clone(), 720.0, 382.0, anchor_center_x, anchor_y);
        let _ = window.set_always_on_top(true);
        let _ = window.set_focusable(true);
        let _ = window.set_ignore_cursor_events(false);
        window.show().map_err(|e| format!("Failed to show island: {e}"))?;
    } else {
        state.visible.store(false, Ordering::Relaxed);
        state.expanded.store(false, Ordering::Relaxed);
        let _ = window.set_ignore_cursor_events(false);
        let _ = window.set_focusable(false);
        sync_island_hit_region(&window, &state);
        window.hide().map_err(|e| format!("Failed to hide island: {e}"))?;
    }

    let _ = app.emit("island-visibility", visible);
    Ok(())
}

#[tauri::command]
fn set_island_interaction(
    app: tauri::AppHandle,
    state: tauri::State<'_, IslandHitState>,
    expanded: bool,
    pill_width: Option<f64>,
    pill_height: Option<f64>,
) -> Result<(), String> {
    if let Some(pw) = pill_width {
        state.pill_width.store(pw.clamp(160.0, 720.0).round() as u32, Ordering::Relaxed);
    }
    if let Some(ph) = pill_height {
        state.pill_height.store(ph.clamp(28.0, 382.0).round() as u32, Ordering::Relaxed);
    }
    state.expanded.store(expanded, Ordering::Relaxed);

    // Window size is fixed; only the hit-rect (pill_width/pill_height) changes.
    if expanded && let Some(window) = app.get_webview_window("island") {
        let _ = window.set_ignore_cursor_events(false);
        let _ = window.set_focus();
    }
    Ok(())
}

#[tauri::command]
fn show_main_window(app: tauri::AppHandle) -> Result<(), String> {
    if let Some(window) = app.get_webview_window("main") {
        let _ = window.show();
        let _ = window.unminimize();
        let _ = window.set_focus();
    }
    Ok(())
}

#[tauri::command]
fn exit_application(app: tauri::AppHandle) {
    app.exit(0);
}

fn request_backend_shutdown() {
    let token = get_session_token().unwrap_or_default();
    let auth_header = if !token.is_empty() {
        format!("Authorization: Bearer {}\r\nX-Session-Token: {}\r\n", token, token)
    } else {
        String::new()
    };

    let addr: std::net::SocketAddr = "127.0.0.1:8765".parse().unwrap();
    if let Ok(mut stream) = std::net::TcpStream::connect_timeout(&addr, std::time::Duration::from_millis(800)) {
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
        .manage(IslandHitState::default())
        .setup(|app| {
            if cfg!(debug_assertions) {
                app.handle().plugin(
                    tauri_plugin_log::Builder::default()
                        .level(log::LevelFilter::Info)
                        .build(),
                )?;
            }

            let show_item = MenuItem::with_id(app, "show", "Показать ассистента", true, None::<&str>)?;
            let hide_item = MenuItem::with_id(app, "hide", "Скрыть в трей", true, None::<&str>)?;
            let separator = PredefinedMenuItem::separator(app)?;
            let quit_item = MenuItem::with_id(app, "quit", "Выход", true, None::<&str>)?;

            let menu = Menu::with_items(app, &[&show_item, &hide_item, &separator, &quit_item])?;

            let mut tray_builder = TrayIconBuilder::new()
                .menu(&menu)
                .tooltip("Assistant")
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

            let tray_icon = tauri::include_image!("icons/32x32.png");
            tray_builder = tray_builder.icon(tray_icon);
            let win_icon = tauri::include_image!("icons/icon.png");
            if let Some(main_win) = app.get_webview_window("main") {
                let _ = main_win.set_icon(win_icon);
            }

            let _tray = tray_builder.build(app)?;
            spawn_island_hit_watcher(app.handle().clone());

            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { api, .. } = event {
                api.prevent_close();
                let _ = window.hide();
                if window.label() == "island" {
                    let app_handle = window.app_handle();
                    let state = app_handle.state::<IslandHitState>();
                    state.visible.store(false, Ordering::Relaxed);
                    state.expanded.store(false, Ordering::Relaxed);
                    let _ = window.set_ignore_cursor_events(false);
                    let _ = window.set_focusable(false);
                    if let Some(webview_win) = app_handle.get_webview_window("island") {
                        sync_island_hit_region(&webview_win, &state);
                    }
                    let _ = app_handle.emit("island-visibility", false);
                }
            }
        })
        .invoke_handler(tauri::generate_handler![
            get_session_token,
            set_island_bounds,
            get_island_anchor,
            get_island_visible,
            set_island_visible,
            set_island_interaction,
            show_main_window,
            exit_application
        ])
        .run(tauri::generate_context!())
        .expect("error while building tauri application");
}
