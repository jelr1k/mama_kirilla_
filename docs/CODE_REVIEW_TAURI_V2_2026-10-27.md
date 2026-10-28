# Code Review: Tauri v2 UI Migration and Integration

**Project:** Mama Kirilla / JARVIS  
**Reviewed branch:** `experimental`  
**Reviewed HEAD:** `5ace7186baed7c1bb32b26cc68ce092a0f052e43` (`feat(ui): migrate claude_ui to ui, archive pyside ui, add full feature parity and gateway service`)  
**Review date:** 2026-10-27  
**Review type:** Static source review. Runtime tests and a production Tauri build were not executed as part of this review.  
**Target architecture:** Tauri v2 + React/Vite frontend, Python backend, HTTP API + WebSocket bridge. PySide UI is archived under `ui_archive/` and must not appear during normal launch.

## Executive summary

The repository contains a real Tauri v2 application scaffold and a substantial React UI, but the migration is not yet consistently wired into the application's launch, API, and test paths. The most urgent problems are:

1. The default launch paths still start the archived PySide UI or Electron, rather than reliably starting the Python backend in headless mode and opening Tauri.
2. REST requests use relative `/api/...` URLs. In Tauri and Vite development mode, these requests target the frontend origin, not the FastAPI server on `127.0.0.1:8765`.
3. Streaming LLM output is not committed to the chat history when generation finishes, so the displayed answer can disappear.
4. Saving settings replaces nested configuration sections instead of merging partial updates, potentially dropping existing settings.
5. The local HTTP/WebSocket gateway accepts requests without authentication and has unrestricted CORS / no WebSocket Origin validation.
6. Existing PySide tests still import modules from the old `ui/` paths and are incompatible with the archive move.

The target should remain **Tauri v2**. Do not redesign the UI framework or reintroduce Electron as a fallback. Treat the current React/Tauri UI as the intended frontend and fix the integration around it.

---

## Findings

### P1 — The normal launch path does not consistently launch Tauri

**Evidence**
- Root `start.bat` invokes `start/bootstrap.py` without adding `--headless` by default.
- `start/main.py` selects the old window path unless `--headless` or `JARVIS_HEADLESS` is set. That path imports `MainWindow` from `ui_archive.main_window` and creates the PySide window.
- `ui/start.bat` runs `npm run app`.
- `ui/package.json` defines `app` as a Vite + Electron launch and maps `start` to `app`.
- Tauri is configured under `ui/src-tauri/`, but neither launcher currently provides one unambiguous route that starts the backend and then launches the Tauri application.

**Required changes**
- Establish one documented, deterministic launch flow for the target architecture: start the Python backend without the archived PySide main window, then start the Tauri v2 frontend.
- Update the root and UI launch scripts so they do not silently launch PySide or Electron.
- Provide separate, clearly named development and packaged-app flows if necessary. The development flow may invoke `tauri dev`; the normal packaged flow should launch the built Tauri application and must not require end users to have Node.js or Rust installed.
- Do not blindly remove all PySide dependencies yet: the headless path currently uses `QApplication` and the tray implementation. Preserve the tray if it is still required, while ensuring the archived `MainWindow` is never created during normal launch.
- Add startup checks and actionable error messages if the backend or Tauri executable is missing or fails to start.

**Acceptance criteria**
- Running the documented normal launcher opens the Tauri v2 window, not a PySide `MainWindow` or Electron window.
- The Python gateway becomes reachable at `http://127.0.0.1:8765` before the frontend attempts API operations.
- Closing the Tauri app follows a deliberate shutdown path and does not leave a stray backend process.
- A failed frontend launch does not silently leave an orphaned backend process running indefinitely.

### P1 — REST API URLs point at the frontend origin, not the Python gateway

**Evidence**
- UI components such as `ui/src/components/Settings.jsx`, `Ollama.jsx`, `Aliases.jsx`, `Workspace.jsx`, `WebsitesSubtab.jsx`, `HistoryModal.jsx`, and `Chat.jsx` use relative URLs such as `fetch('/api/settings')` and `fetch('/api/websites')`.
- `ui/vite.config.js` configures the Vite server but contains no `/api` proxy to the Python backend.
- `ui/src-tauri/tauri.conf.json` loads the built frontend directly in a Tauri window; its origin is not the FastAPI gateway origin.
- `assistantSocket.js` correctly uses a WebSocket URL for `ws://127.0.0.1:8765/ws`, which highlights the mismatch: HTTP calls do not use the same backend base URL.

**Impact**
Settings, model lists, microphones, aliases, workspace, website management, statistics, updates, shutdown and other REST-backed functions can fail in both Tauri and Vite development mode because `/api/...` resolves against the frontend origin.

**Required changes**
- Centralize the backend URL in one frontend API client/configuration module.
- Route all HTTP requests to the gateway at `http://127.0.0.1:8765`; allow an explicit environment override for development/testing if needed.
- Use the same centralized configuration for the WebSocket URL.
- Alternatively, a Vite proxy may help development, but it does not solve the packaged Tauri build on its own. The production Tauri path must be handled explicitly.
- Do not scatter hard-coded addresses throughout components.

**Acceptance criteria**
- Verify HTTP and WebSocket connectivity in both `tauri dev` and a production Tauri build.
- Exercise at least settings load/save, model discovery, aliases, workspace, websites, statistics, and shutdown against the real local gateway.
- When the backend is unavailable, show a visible connection/error state rather than silently failing.

### P1 — Completed streamed LLM responses disappear from the chat

**Evidence**
- `services/chat_service.py` emits `chat.chunk` events while streaming tokens and emits `chat.generation_finished` when generation finishes. The streamed-answer path does not publish the completed accumulated text as `chat.direct_response`.
- `ui/src/services/assistantSocket.js` appends incoming `chat.chunk` values to `currentChunk`; on `chat.status` with status `idle`, it turns `isStreaming` off.
- `ui/src/components/Chat.jsx` renders the temporary chunk bubble only while `status === 'think' && isStreaming && currentChunk`. It adds a permanent assistant message only when `lastResponse` changes, but the streamed LLM path does not provide that final `chat.response` event.

**Impact**
The answer can be visible while it streams and then vanish when generation finishes. Direct router responses and streamed model responses therefore have inconsistent behaviour.

**Required changes**
- Establish a clear final-response event contract. Prefer having the backend publish the final accumulated response once generation completes, while retaining chunk events for live rendering.
- Update the frontend so the final response is committed to the chat message list exactly once, and the temporary streaming bubble is then removed.
- Ensure error, cancellation, queued prompts and consecutive identical answers do not duplicate or lose messages.

**Acceptance criteria**
- Add a regression test that sends an LLM prompt, receives several chunks, receives completion, and verifies that the complete answer remains visible after the UI returns to idle.
- Add coverage for a direct router response and for a failed generation.

### P1 — Settings updates can replace nested config sections with partial objects

**Evidence**
- `services/gateway_service.py` handles `POST /api/settings` by iterating over the payload and calling `cfg.set(k, v)` for each key.
- `core/config_manager.py` implements `set()` as a direct assignment to `self.data[key]` followed by saving; it does not merge dictionaries.
- `ui/src/components/Settings.jsx` sends a `voice` object containing only UI-edited fields. Existing fields such as `device`, `compute_type`, `language`, `sample_rate`, and other backend settings are not all included in that payload.

**Impact**
Saving settings can erase unrelated keys from an existing nested section. The application may silently lose backend configuration that the form did not intend to change.

**Required changes**
- Implement a deliberate partial-update/merge strategy for nested settings, or send a complete schema-backed configuration object. Do not combine these approaches inconsistently.
- Validate incoming field types and acceptable ranges before saving.
- Keep persistence and applying settings consistent: report errors to the UI if validation, persistence, or application fails.

**Acceptance criteria**
- Add a test that starts with extra keys in `voice`, `tts`, and `ollama`, saves a subset of settings, and verifies unrelated keys remain intact.
- Verify persisted settings can be reloaded without missing required fields.

### P1 — Local API and WebSocket gateway have no meaningful access control

**Evidence**
- `services/gateway_service.py` configures CORS with `allow_origins=["*"]`, `allow_methods=["*"]`, and `allow_headers=["*"]` while also allowing credentials.
- The WebSocket endpoint at `/ws` accepts connections without validating the request Origin or requiring a session token.
- The gateway exposes operations that mutate settings and tool permissions, configure autostart, start updates, open URLs, test audio devices, and shut down the application.

**Impact**
A local service is not automatically protected from browser-originated requests. A hostile web page or another local process may attempt to access the gateway and trigger actions. The WebSocket path is also not protected by the CORS middleware.

**Required changes**
- Restrict HTTP CORS to the exact origins used by the Tauri production WebView and the local development server. Do not use a wildcard allow-all policy.
- Validate WebSocket Origin as well; do not assume CORS middleware protects WebSockets.
- Add a suitable local authentication/handshake mechanism for HTTP and WebSocket requests, ideally with a per-run secret passed securely between the launcher/Tauri layer and backend rather than embedded as a constant in frontend assets.
- Validate action payloads and reject unexpected operations or malformed settings.
- Keep the server bound to loopback unless remote access is an explicit product requirement.

**Acceptance criteria**
- Approved Tauri and dev origins can connect.
- An unrelated browser origin cannot read settings or trigger gateway operations.
- Unauthenticated WebSocket clients cannot send `chat.send`, `voice.start`, `app.quit`, or other actions.
- Add tests for rejected Origins and missing/invalid authentication.

### P1 — Existing tests still import the old PySide UI layout

**Evidence**
- `tests/test_ui_smoke.py` imports `ChatPage`, `SettingsPage`, `StatisticsPage`, and `ToolsPage` from `ui.*` modules.
- `tests/test_ui_animations.py` imports from `ui.animations` and `ui.animations.splash_screen`.
- The reviewed branch removes those active paths and moves the Python UI modules to `ui_archive/`.

**Impact**
The Python test suite is likely to fail during test collection with import errors before it can validate the migrated application. The existing smoke tests also validate the archived PySide UI rather than the active Tauri UI.

**Required changes**
- Decide whether the old tests should remain as explicitly archived regression tests (then update their imports to `ui_archive` and label them accordingly) or be removed from the active test suite.
- Add active UI verification for the React/Tauri app, including frontend build checks and Python gateway integration tests. Do not simply delete the old tests without replacing coverage of important behaviours.
- Update the CI workflow to install Node dependencies and validate the React build. Add a Tauri/Rust check on a suitable runner.

**Acceptance criteria**
- `pytest` completes test collection successfully on `experimental`.
- `npm ci` and `npm run build` pass in CI.
- The new Tauri app's basic launch/build path is checked automatically.

### P2 — Electron entry files and scripts conflict with the declared Tauri target

**Evidence**
- `ui/package.json` has `"main": "main.js"`; the `app` script launches Electron; `start` calls `app`; and Electron-specific dependencies include `electron`, `concurrently`, `cross-env`, and `wait-on`.
- `ui/main.js` creates an Electron `BrowserWindow` and loads `preload.js`.
- `ui/preload.js` exposes `electronAPI` through Electron's `contextBridge`.
- Tauri uses `ui/src-tauri/src/main.rs`, `ui/src-tauri/src/lib.rs`, and `ui/src-tauri/tauri.conf.json`; the Rust application does not reference `main.js` or `preload.js`.
- `ui/start.bat` currently calls `npm run app`, so it selects the Electron route.

**Decision**
The reviewed Tauri configuration has no use for `ui/main.js` or `ui/preload.js`. They are Electron-only leftovers and are not required by the Tauri v2 application as currently implemented.

**Required changes**
- Remove Electron-only scripts and dependencies from `ui/package.json`, remove the Electron `main` entry, and regenerate `ui/package-lock.json`.
- Delete `ui/main.js` and `ui/preload.js` from the active UI directory once a repository-wide reference check confirms there are no consumers. If there is a documented historical reason to retain them, move them to an explicitly named archive rather than leaving them in the active launch path.
- Add clear scripts such as `tauri:dev` and `tauri:build`; make `ui/start.bat` call the Tauri v2 route rather than Electron.
- Preserve the Tauri v2 dependencies and Rust app configuration.

**Acceptance criteria**
- A repository-wide search finds no active Electron launch references.
- `npm ci`, `npm run build`, and the documented Tauri dev/build commands work from a clean checkout.

### P2 — Autostart registry entry points one directory above the project

**Evidence**
- In `services/gateway_service.py`, `_set_autostart()` builds the launcher path using `Path(__file__).resolve().parent.parent.parent / "start.bat"`.
- Since the file is located under `<project>/services/`, `parent.parent` is the project root; the additional `.parent` moves above the project. The resulting path does not identify `<project>/start.bat` in the reviewed source layout.

**Impact**
The UI can report that autostart is enabled while Windows is configured to run a non-existent or unintended path.

**Required changes**
- Resolve the launcher using the canonical application-root helper, and account explicitly for the packaged installation layout.
- Return a failure to the UI if the launcher path does not exist or the registry write fails.

**Acceptance criteria**
- Add a unit test that verifies the constructed registry command points to the intended launcher for the source and supported packaged layouts.
- Toggling autostart on/off is reflected accurately by the settings UI.

### P2 — Tauri Content Security Policy is disabled

**Evidence**
- `ui/src-tauri/tauri.conf.json` sets `app.security.csp` to `null`.
- `ui/index.html` loads a stylesheet from Google Fonts.

**Required changes**
- Replace the disabled CSP with an explicit policy for the shipped UI. Allow only the required local backend HTTP/WebSocket endpoints and required asset/font sources, or bundle the font locally and reduce external sources.
- Verify the policy against both the Tauri development origin and packaged build. Do not loosen it to `*` merely to make API requests pass.

**Acceptance criteria**
- The frontend works with an explicit CSP and does not require arbitrary remote script/connect permissions.

### P2 — Whisper and TTS download polling can run forever after a failed download

**Evidence**
- `ui/src/components/Settings.jsx` starts recurring polls for Whisper and TTS status and clears the timer only if a model/voice reaches `installed`.
- `services/gateway_service.py` starts the downloads in daemon threads and logs exceptions, but the exposed status endpoints do not report a completed failure state for these download requests.

**Impact**
A failed download can leave the UI stuck in a downloading state and continue polling indefinitely.

**Required changes**
- Expose explicit queued/downloading/installed/failed states, including an actionable error message.
- Add timeout/cancellation and cleanup for polling timers when the component unmounts or the operation ends.

**Acceptance criteria**
- Failed, interrupted, and successful downloads all end polling and show the correct terminal state.

### P2 — CI does not validate the active Tauri frontend and does not run on direct pushes to `experimental`

**Evidence**
- `.github/workflows/tests.yml` push triggers list `osnova` and `main`, but not `experimental`.
- The workflow runs Python compilation and pytest but has no Node setup, `npm ci`, Vite build, Rust setup, or Tauri build/check step.

**Required changes**
- Include `experimental` in push validation while this branch is being used for integration work, or use pull-request-only validation with a clearly documented policy.
- Add a frontend build job and a Tauri/Rust validation job appropriate to supported platforms.
- Ensure the test workflow catches stale imports from the archived UI.

**Acceptance criteria**
- A push or PR containing a broken React build or Python test collection failure is reported by CI.

### P3 — Updater defaults still use the old repository name

**Evidence**
- `services/update_checker.py` declares `DEFAULT_REPOSITORY = "jelr1k/localjarvisgolos"`.
- The gateway's fallback releases URL also uses the old repository name.
- The canonical repository is now `jelr1k/mama_kirilla_`.

**Required changes**
- Replace stale default/fallback URLs with the canonical repository path and search the codebase/docs for any other active references to the old name.
- Keep historical migration notes intact where the old name is useful context.

**Acceptance criteria**
- Update checks and the release-page link use the canonical repository and have a test for the configured repository value.

---

## Recommended implementation order

1. **Make launch behaviour deterministic:** headless Python backend + Tauri v2 window; remove Electron from active launch scripts.
2. **Fix API routing and gateway access control:** central API client, exact allowed origins, WebSocket Origin/auth validation.
3. **Fix correctness bugs:** persistent streamed answers and safe nested settings updates.
4. **Repair tests and CI:** remove stale active imports, add frontend/Tauri build validation, add regression tests for the findings above.
5. **Repair supporting integration:** autostart path, download status lifecycle, CSP, canonical updater repository.
6. **Run and report final checks:** Python tests, frontend build, Tauri check/build, and a manual smoke test of the packaged app.

## Minimum end-to-end smoke test

- Launch from the documented entry point and verify that only the Tauri v2 frontend is displayed.
- Verify backend health at `http://127.0.0.1:8765/health` and WebSocket connection at `/ws`.
- Load and save settings; verify unrelated nested settings survive the save and application restart.
- Send a direct router command and an LLM prompt. Verify that streamed output remains in the chat after generation completes.
- Check model discovery, microphone list/test, voice start/stop, wake-word toggle, TTS test, aliases, workspace, websites, and statistics.
- Check update status without applying an update; test autostart enable/disable.
- Close the Tauri window and verify the backend shuts down cleanly according to the intended lifecycle policy.
- Confirm that a foreign browser origin and an unauthenticated WebSocket client cannot invoke local actions.

## Agent execution boundaries

- Work against the current `experimental` working copy only. Do not merge into `main` or `osnova`.
- Do not push, create commits, create PRs, or change GitHub state unless the project owner explicitly requests it.
- Do not reintroduce Electron or move active code back into the archived PySide UI.
- Keep changes focused, inspect the diff before completion, and report exactly which tests/builds were actually run. Do not claim a check passed unless it was executed.

## Review limitations

This document is based on static inspection of the source at the HEAD listed above. The findings should be verified while implementing fixes, and runtime behaviour should be tested locally. No source files in the GitHub repository were changed as part of this review.
