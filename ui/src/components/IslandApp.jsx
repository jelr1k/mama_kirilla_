import React, { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { Icon } from './Icons';
import { apiGet, apiPost } from '../services/api';
import { useAssistant } from '../services/useAssistant';
import './IslandApp.css';

const ISLAND_TABS = [
  { id: 'main', label: 'Главное', icon: 'home' },
  { id: 'protocols', label: 'Протоколы', icon: 'zap' },
  { id: 'chat', label: 'Чат', icon: 'chat' },
  { id: 'tools', label: 'Утилиты', icon: 'clock' },
];

const CONFIG_STORAGE_KEY = 'kirieshcka_island_config';
const POS_STORAGE_KEY = 'kirieshcka_island_pos';

export const SYSTEM_QUICK_ACTIONS = [
  { id: 'sys:screenshot', action: 'screenshot', label: 'Скриншот', sub: 'Система', icon: 'camera' },
  { id: 'sys:open_screenshots', action: 'open_screenshots', label: 'Скриншоты', sub: 'Папка', icon: 'folder' },
  { id: 'sys:open_downloads', action: 'open_downloads', label: 'Загрузки', sub: 'Папка', icon: 'folder' },
  { id: 'sys:empty_bin', action: 'empty_bin', label: 'Корзина', sub: 'Очистить', icon: 'trash' },
  { id: 'sys:lock', action: 'lock', label: 'Блок ПК', sub: 'Система', icon: 'lock' },
];

const FALLBACK_COMMAND_CATALOG = [
  { id: 'zapret_start', name: 'Запрет Discord/YouTube', category: 'network', commands: ['запрет'] },
  { id: 'vpn_connect', name: 'VPN-клиент', category: 'network', commands: ['впн'] },
  { id: 'vpn_status', name: 'Статус VPN и Запрета', category: 'network', commands: ['статус впн'] },
  { id: 'system_telemetry', name: 'Телеметрия ПК', category: 'system', commands: ['телеметрия'] },
  { id: 'date_time', name: 'Время и дата', category: 'system', commands: ['сколько времени'] },
  { id: 'jarvis_minimize', name: 'Свернуть окно', category: 'system', commands: ['свернись'] },
  { id: 'jarvis_maximize', name: 'Развернуть окно', category: 'system', commands: ['развернись'] },
  { id: 'jarvis_restore', name: 'Восстановить окно', category: 'system', commands: ['восстанови окно'] },
  { id: 'jarvis_shutdown', name: 'Закрыть ассистента', category: 'system', commands: ['закрой себя'] },
  { id: 'apply_mouse_settings', name: 'Настройки мыши', category: 'devices', commands: ['мышь'] },
  { id: 'media_play_pause', name: 'Пауза / Плей', category: 'media', commands: ['пауза'] },
  { id: 'media_next', name: 'Следующий трек', category: 'media', commands: ['вперед'] },
  { id: 'media_prev', name: 'Предыдущий трек', category: 'media', commands: ['назад'] },
  { id: 'media_stop', name: 'Стоп музыки', category: 'media', commands: ['стоп'] },
  { id: 'media_volume_up', name: 'Громче', category: 'media', commands: ['сделай громче'] },
  { id: 'media_volume_down', name: 'Тише', category: 'media', commands: ['сделай тише'] },
  { id: 'media_mute_toggle', name: 'Переключить звук', category: 'media', commands: ['переключи звук'] },
  { id: 'ollama_status', name: 'Статус Ollama', category: 'ai', commands: ['статус ollama'] },
  { id: 'ollama_start', name: 'Запустить Ollama', category: 'ai', commands: ['запусти ollama'] },
  { id: 'ollama_stop', name: 'Остановить Ollama', category: 'ai', commands: ['останови ollama'] },
  { id: 'model_unload', name: 'Выгрузить модель', category: 'ai', commands: ['выгрузи модель'] },
  { id: 'clear_chat', name: 'Очистить чат', category: 'ai', commands: ['очисти чат'] },
];

const DUPLICATE_SYSTEM_CMD_IDS = new Set([
  'take_screenshot',
  'empty_recycle_bin',
  'lock_pc',
]);

const CATEGORY_LABELS = {
  network: 'Сеть и VPN',
  media: 'Медиа и звук',
  system: 'Система',
  files: 'Файлы',
  apps: 'Приложения',
  devices: 'Девайсы',
  ai: 'ИИ и чат',
};

function pickCommandIcon(cmdId, category) {
  if (cmdId.includes('minimize')) return 'minimize';
  if (cmdId.includes('maximize') || cmdId.includes('restore')) return 'maximize';
  if (cmdId.includes('shutdown')) return 'power';
  if (cmdId.includes('vpn') || cmdId.includes('zapret')) return 'shield';
  if (cmdId.includes('mouse')) return 'game';
  if (cmdId.includes('date_time')) return 'clock';
  if (cmdId.includes('telemetry')) return 'cpu';
  if (cmdId.includes('clear_chat')) return 'trash';
  if (category === 'media') return 'music';
  if (category === 'protocols') return 'zap';
  if (category === 'files') return 'folder';
  if (category === 'apps') return 'web';
  if (category === 'ai') return 'brain';
  return 'cmd';
}

export const DEFAULT_ISLAND_CONFIG = {
  enabledTabs: ['main', 'protocols', 'chat', 'tools'],
  mainModules: {
    voice: true,
    media: true,
    actions: true,
    telemetry: true,
  },
  quickActions: [
    'sys:screenshot',
    'sys:open_screenshots',
    'sys:empty_bin',
    'sys:lock',
  ],
};

function loadIslandConfig() {
  try {
    const raw = localStorage.getItem(CONFIG_STORAGE_KEY);
    if (!raw) return DEFAULT_ISLAND_CONFIG;
    const parsed = JSON.parse(raw);
    const validTabIds = ISLAND_TABS.map((t) => t.id);
    const enabledTabs = Array.isArray(parsed?.enabledTabs)
      ? parsed.enabledTabs.filter((id) => validTabIds.includes(id))
      : DEFAULT_ISLAND_CONFIG.enabledTabs;
    const quickActions = Array.isArray(parsed?.quickActions)
      ? parsed.quickActions.filter(
        (id) =>
          typeof id === 'string'
          && id.trim()
          && !id.startsWith('proto:')
          && !id.startsWith('cmd:protocol_')
      )
      : DEFAULT_ISLAND_CONFIG.quickActions;
    return {
      enabledTabs: enabledTabs.length > 0 ? enabledTabs : DEFAULT_ISLAND_CONFIG.enabledTabs,
      mainModules: {
        ...DEFAULT_ISLAND_CONFIG.mainModules,
        ...(parsed?.mainModules && typeof parsed.mainModules === 'object' ? parsed.mainModules : {}),
      },
      quickActions,
    };
  } catch {
    return DEFAULT_ISLAND_CONFIG;
  }
}

function loadSavedAnchor() {
  try {
    const raw = localStorage.getItem(POS_STORAGE_KEY);
    if (!raw) return { centerX: null, y: null, dockedTop: true };
    const parsed = JSON.parse(raw);
    if (typeof parsed?.centerX === 'number' && typeof parsed?.y === 'number') {
      return {
        centerX: Math.round(parsed.centerX),
        y: Math.round(parsed.y),
        dockedTop: parsed.dockedTop !== undefined ? Boolean(parsed.dockedTop) : parsed.y <= 8,
      };
    }
  } catch {
    return { centerX: null, y: null, dockedTop: true };
  }
  return { centerX: null, y: null, dockedTop: true };
}

const STATUS_LABELS = {
  idle: 'Готов к команде',
  listen: 'Слушаю...',
  think: 'Думаю...',
  speak: 'Отвечаю...',
};

const EN_LAYOUT = "`qwertyuiop[]asdfghjkl;'zxcvbnm,./~QWERTYUIOP{}ASDFGHJKL:\"ZXCVBNM<>?@#$^&";
const RU_LAYOUT = "ёйцукенгшщзхъфывапролджэячсмитьбю.ЁЙЦУКЕНГШЩЗХЪФЫВАПРОЛДЖЭЯЧСМИТЬБЮ,\"№;:?";

export function fixKeyboardLayout(text) {
  if (!text) return '';
  const enToRu = new Map();
  const ruToEn = new Map();
  for (let i = 0; i < EN_LAYOUT.length; i += 1) {
    enToRu.set(EN_LAYOUT[i], RU_LAYOUT[i]);
    ruToEn.set(RU_LAYOUT[i], EN_LAYOUT[i]);
  }
  const hasCyrillic = /[а-яёА-ЯЁ]/.test(text);
  const map = hasCyrillic ? ruToEn : enToRu;
  return Array.from(text)
    .map((ch) => map.get(ch) ?? ch)
    .join('');
}

export function formatTimer(totalSeconds) {
  const safe = Math.max(0, Math.floor(totalSeconds));
  const m = Math.floor(safe / 60);
  const s = safe % 60;
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}

function playTimerBeep() {
  try {
    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    if (!AudioCtx) return;
    const ctx = new AudioCtx();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = 'sine';
    osc.frequency.setValueAtTime(660, ctx.currentTime);
    osc.frequency.exponentialRampToValueAtTime(880, ctx.currentTime + 0.18);
    gain.gain.setValueAtTime(0.08, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.35);
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start();
    osc.stop(ctx.currentTime + 0.36);
  } catch {
    // Ignore audio context restriction
  }
}

const isTauri = () => typeof window !== 'undefined' && Boolean(window.__TAURI_INTERNALS__);

export default function IslandApp({ previewMode = false, onClosePreview }) {
  const {
    connected,
    status,
    assistantName,
    voskText,
    lastTranscript,
    lastResponse,
    currentChunk,
    isStreaming,
    telemetry,
    messages,
    sendChatMessage,
    clearChatMessages,
    startVoice,
    stopVoice,
    stopTts,
  } = useAssistant();

  const [phase, setPhase] = useState('collapsed'); // 'collapsed' | 'expanded' | 'closing'
  const [pinned, setPinned] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [settingsSection, setSettingsSection] = useState('layout'); // 'layout' | 'actions'
  const [actionSearch, setActionSearch] = useState('');
  const [config, setConfig] = useState(loadIslandConfig);
  const [activeTab, setActiveTab] = useState(() => loadIslandConfig().enabledTabs[0] || 'main');
  const [anchorPos, setAnchorPos] = useState(loadSavedAnchor);
  const [previewOffset, setPreviewOffset] = useState(() => {
    const saved = loadSavedAnchor();
    return previewMode && saved.centerX !== null && saved.y !== null
      ? { x: saved.centerX, y: saved.y }
      : { x: 0, y: 0 };
  });

  const [clock, setClock] = useState(() =>
    new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  );

  // Toast / transient activity banner in notch
  const [toastText, setToastText] = useState('');
  const toastTimerRef = useRef(null);
  const shrinkTimerRef = useRef(null);
  const suppressClickRef = useRef(false);
  const isDraggingRef = useRef(false);
  const ignoreMoveUntilRef = useRef(0);
  const anchorPosRef = useRef(anchorPos);
  const phaseRef = useRef(phase);

  useEffect(() => {
    anchorPosRef.current = anchorPos;
    phaseRef.current = phase;
  }, [anchorPos, phase]);

  const isExpandedVisual = phase === 'expanded';
  const isClosing = phase === 'closing';
  const showExpandedDom = phase === 'expanded' || phase === 'closing';

  const visibleTabs = useMemo(() => {
    const list = ISLAND_TABS.filter((t) => config.enabledTabs.includes(t.id));
    return list.length > 0 ? list : ISLAND_TABS;
  }, [config.enabledTabs]);

  // Quick command & chat inputs
  const [quickCmd, setQuickCmd] = useState('');
  const quickCmdInputRef = useRef(null);
  const [chatInput, setChatInput] = useState('');
  const chatEndRef = useRef(null);

  // Media & Volume state
  const [volume, setVolume] = useState(50);
  const [muted, setMuted] = useState(false);

  // Protocols & Command catalog
  const [protocols, setProtocols] = useState([]);
  const [catalogCommands, setCatalogCommands] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');

  // Notes & Timer & Text utilities
  const [noteText, setNoteText] = useState(() => {
    try {
      return localStorage.getItem('kirieshcka_island_note') || '';
    } catch {
      return '';
    }
  });
  const [timerSeconds, setTimerSeconds] = useState(5 * 60);
  const [timerRunning, setTimerRunning] = useState(false);
  const [textUtilInput, setTextUtilInput] = useState('');

  // Sliding tab indicator measurement
  const tabRefs = useRef({});
  const [indicatorStyle, setIndicatorStyle] = useState({ width: 0, x: 0 });

  const showToast = useCallback((msg, durationMs = 2600) => {
    if (!msg) return;
    setToastText(msg);
    if (toastTimerRef.current) clearTimeout(toastTimerRef.current);
    toastTimerRef.current = setTimeout(() => {
      setToastText('');
    }, durationMs);
  }, []);

  const persistAnchor = useCallback((nextAnchor) => {
    setAnchorPos(nextAnchor);
    anchorPosRef.current = nextAnchor;
    try {
      if (nextAnchor.centerX === null || nextAnchor.y === null) {
        localStorage.removeItem(POS_STORAGE_KEY);
      } else {
        localStorage.setItem(POS_STORAGE_KEY, JSON.stringify(nextAnchor));
      }
    } catch {
      // Ignore storage error
    }
  }, []);

  const persistConfig = useCallback((nextConfig) => {
    setConfig(nextConfig);
    try {
      localStorage.setItem(CONFIG_STORAGE_KEY, JSON.stringify(nextConfig));
    } catch {
      // Ignore storage error
    }
  }, []);

  // Ensure activeTab is always among enabled tabs
  useEffect(() => {
    if (!visibleTabs.some((t) => t.id === activeTab)) {
      setActiveTab(visibleTabs[0].id);
    }
  }, [visibleTabs, activeTab]);

  // Update clock every 15s
  useEffect(() => {
    const tick = () => {
      setClock(new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }));
    };
    const id = setInterval(tick, 15000);
    return () => clearInterval(id);
  }, []);

  // Persist note
  useEffect(() => {
    try {
      localStorage.setItem('kirieshcka_island_note', noteText);
    } catch {
      // Ignore storage error
    }
  }, [noteText]);

  // Countdown timer
  useEffect(() => {
    if (!timerRunning) return undefined;
    const id = setInterval(() => {
      setTimerSeconds((prev) => {
        if (prev <= 1) {
          setTimerRunning(false);
          playTimerBeep();
          showToast('Таймер завершен!', 4000);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(id);
  }, [timerRunning, showToast]);

  // Scroll chat to bottom when expanded on chat tab
  useEffect(() => {
    if (isExpandedVisual && !showSettings && activeTab === 'chat') {
      chatEndRef.current?.scrollIntoView?.({ behavior: 'smooth' });
    }
  }, [isExpandedVisual, showSettings, activeTab, messages, currentChunk]);

  // Measure sliding tab indicator
  useLayoutEffect(() => {
    if (!showExpandedDom || showSettings) return;
    const el = tabRefs.current[activeTab];
    if (el) {
      setIndicatorStyle({
        width: el.offsetWidth,
        x: el.offsetLeft - 3,
      });
    }
  }, [showExpandedDom, showSettings, activeTab, visibleTabs]);

  const hasNotchActivity = Boolean(
    status !== 'idle' || toastText || timerRunning
  );
  const hasNotchActivityRef = useRef(hasNotchActivity);
  useEffect(() => {
    hasNotchActivityRef.current = hasNotchActivity;
  }, [hasNotchActivity]);

  const syncTauriInteraction = useCallback(async (expanded, pillWidth, pillHeight) => {
    if (previewMode || !isTauri()) return;
    try {
      const { invoke } = await import('@tauri-apps/api/core');
      await invoke('set_island_interaction', {
        expanded,
        pillWidth,
        pillHeight,
      });
    } catch {
      // Ignore outside Tauri
    }
  }, [previewMode]);

  const applyTauriBounds = useCallback(async (width, height, overrideAnchor = null) => {
    if (previewMode || !isTauri()) return null;
    try {
      const { invoke } = await import('@tauri-apps/api/core');
      const targetAnchor = overrideAnchor ?? anchorPosRef.current;
      ignoreMoveUntilRef.current = Date.now() + 320;
      const args = { width, height };
      if (typeof targetAnchor?.centerX === 'number' && typeof targetAnchor?.y === 'number') {
        args.anchorCenterX = Math.round(targetAnchor.centerX);
        args.anchorY = Math.round(targetAnchor.y);
      }
      const res = await invoke('set_island_bounds', args);
      if (res && typeof res.dockedTop === 'boolean') {
        setAnchorPos((prev) => ({ ...prev, dockedTop: res.dockedTop }));
      }
      return res;
    } catch {
      return null;
    }
  }, [previewMode]);

  // Track user-initiated window drag moves & restore saved position on visibility changes
  useEffect(() => {
    if (previewMode || !isTauri()) return undefined;
    let unlistenMove = null;
    let unlistenVis = null;
    let moveDebounce = null;
    let disposed = false;

    const setupListeners = async () => {
      try {
        const { getCurrentWebviewWindow } = await import('@tauri-apps/api/webviewWindow');
        const { listen } = await import('@tauri-apps/api/event');
        const { invoke } = await import('@tauri-apps/api/core');
        const win = getCurrentWebviewWindow();

        // Keep fixed 720x382 transparent surface and apply saved anchor on mount
        const saved = loadSavedAnchor();
        if (saved.centerX !== null && saved.y !== null) {
          await applyTauriBounds(720, 382, saved);
        }
        const active = hasNotchActivityRef.current;
        await syncTauriInteraction(false, active ? 356 : 224, active ? 48 : 38);

        const unMove = await win.onMoved(() => {
          if (disposed || Date.now() < ignoreMoveUntilRef.current) return;
          if (moveDebounce) clearTimeout(moveDebounce);
          moveDebounce = setTimeout(async () => {
            if (disposed) return;
            try {
              const snapTop = phaseRef.current === 'collapsed';
              if (snapTop) ignoreMoveUntilRef.current = Date.now() + 200;
              const info = await invoke('get_island_anchor', { snapTop });
              if (info && typeof info.centerX === 'number' && typeof info.y === 'number') {
                persistAnchor({
                  centerX: info.centerX,
                  y: info.y,
                  dockedTop: Boolean(info.dockedTop),
                });
              }
            } catch {
              // Ignore
            } finally {
              isDraggingRef.current = false;
            }
          }, 120);
        });

        const unVis = await listen('island-visibility', (event) => {
          if (disposed) return;
          if (event.payload) {
            setPhase('collapsed');
            setShowSettings(false);
            const isActive = hasNotchActivityRef.current;
            syncTauriInteraction(false, isActive ? 356 : 224, isActive ? 48 : 38);
          } else {
            setPhase('collapsed');
            setShowSettings(false);
          }
        });

        if (disposed) {
          unMove();
          unVis();
        } else {
          unlistenMove = unMove;
          unlistenVis = unVis;
        }
      } catch {
        // Ignore outside Tauri
      }
    };

    setupListeners();
    return () => {
      disposed = true;
      if (moveDebounce) clearTimeout(moveDebounce);
      if (typeof unlistenMove === 'function') unlistenMove();
      if (typeof unlistenVis === 'function') unlistenVis();
    };
  }, [previewMode, applyTauriBounds, syncTauriInteraction, persistAnchor]);

  // Update collapsed hit-test box without resizing the HWND
  useEffect(() => {
    if (previewMode || !isTauri() || phase !== 'collapsed') return;
    syncTauriInteraction(false, hasNotchActivity ? 356 : 224, hasNotchActivity ? 48 : 38);
  }, [hasNotchActivity, phase, previewMode, syncTauriInteraction]);

  // Cleanup timers on unmount
  useEffect(() => {
    return () => {
      if (toastTimerRef.current) clearTimeout(toastTimerRef.current);
      if (shrinkTimerRef.current) clearTimeout(shrinkTimerRef.current);
    };
  }, []);

  // Fetch data when expanded
  const refreshPanelData = async () => {
    try {
      const [mediaRes, protoRes, cmdRes] = await Promise.allSettled([
        apiGet('/api/media/status'),
        apiGet('/api/protocols'),
        apiGet('/api/commands'),
      ]);
      if (mediaRes.status === 'fulfilled' && mediaRes.value) {
        if (typeof mediaRes.value.volume === 'number') setVolume(mediaRes.value.volume);
        if (typeof mediaRes.value.muted === 'boolean') setMuted(mediaRes.value.muted);
      }
      if (protoRes.status === 'fulfilled' && Array.isArray(protoRes.value?.protocols)) {
        setProtocols(protoRes.value.protocols);
      }
      if (cmdRes.status === 'fulfilled' && Array.isArray(cmdRes.value?.commands)) {
        setCatalogCommands(cmdRes.value.commands);
      }
    } catch {
      // Offline backend is handled gracefully
    }
  };

  useEffect(() => {
    if (phase === 'expanded') {
      refreshPanelData();
    }
  }, [phase]);

  const handleOpenIsland = useCallback(() => {
    if (suppressClickRef.current) {
      suppressClickRef.current = false;
      return;
    }
    if (shrinkTimerRef.current) {
      clearTimeout(shrinkTimerRef.current);
      shrinkTimerRef.current = null;
    }

    if (!previewMode && isTauri()) {
      syncTauriInteraction(true, 688, 352);
    }
    setPhase('expanded');
  }, [previewMode, syncTauriInteraction]);

  const handleCollapseIsland = useCallback(() => {
    if (phaseRef.current !== 'expanded') return;
    if (shrinkTimerRef.current) {
      clearTimeout(shrinkTimerRef.current);
      shrinkTimerRef.current = null;
    }
    setPhase('closing');

    shrinkTimerRef.current = setTimeout(() => {
      shrinkTimerRef.current = null;
      setPhase('collapsed');
      setShowSettings(false);
      if (!previewMode && isTauri()) {
        const active = Boolean(status !== 'idle' || toastText || timerRunning);
        syncTauriInteraction(false, active ? 356 : 224, active ? 48 : 38);
      }
    }, 310);
  }, [previewMode, syncTauriInteraction, status, toastText, timerRunning]);

  // Collapse on Escape or window blur (unless pinned or actively dragging)
  useEffect(() => {
    const onKeyDown = (e) => {
      if (e.key === 'Escape' && phase === 'expanded') {
        handleCollapseIsland();
      }
    };
    const onBlur = () => {
      if (!previewMode && phase === 'expanded' && !pinned && !isDraggingRef.current) {
        handleCollapseIsland();
      }
    };
    window.addEventListener('keydown', onKeyDown);
    window.addEventListener('blur', onBlur);
    return () => {
      window.removeEventListener('keydown', onKeyDown);
      window.removeEventListener('blur', onBlur);
    };
  }, [phase, pinned, previewMode, handleCollapseIsland]);

  const beginPointerDrag = useCallback((e, { allowAnyTarget = false } = {}) => {
    if (e.button !== 0) return;
    if (!allowAnyTarget && e.target.closest('button, input, textarea, select, a, [role="tab"]')) {
      return;
    }

    const startX = e.clientX;
    const startY = e.clientY;
    const baseOffset = { ...previewOffset };
    let started = false;

    const cleanup = () => {
      window.removeEventListener('pointermove', onMove);
      window.removeEventListener('pointerup', onUp);
      window.removeEventListener('pointercancel', onUp);
    };

    const onMove = async (mv) => {
      const dx = mv.clientX - startX;
      const dy = mv.clientY - startY;
      if (!started && Math.hypot(dx, dy) < 5) return;

      if (!started) {
        started = true;
        suppressClickRef.current = true;
        if (!previewMode && isTauri()) {
          cleanup();
          isDraggingRef.current = true;
          try {
            const { getCurrentWebviewWindow } = await import('@tauri-apps/api/webviewWindow');
            await getCurrentWebviewWindow().startDragging();
          } catch {
            isDraggingRef.current = false;
          }
          return;
        }
      }

      if (previewMode || !isTauri()) {
        const nextY = Math.max(0, baseOffset.y + dy);
        const nextX = baseOffset.x + dx;
        setPreviewOffset({ x: nextX, y: nextY });
      }
    };

    const onUp = (upEv) => {
      cleanup();
      if (started && (previewMode || !isTauri())) {
        const dx = upEv.clientX - startX;
        const dy = upEv.clientY - startY;
        const finalY = Math.max(0, baseOffset.y + dy);
        const snappedY = finalY <= 8 ? 0 : Math.round(finalY);
        const finalX = Math.round(baseOffset.x + dx);
        setPreviewOffset({ x: finalX, y: snappedY });
        persistAnchor({ centerX: finalX, y: snappedY, dockedTop: snappedY <= 8 });
      }
    };

    window.addEventListener('pointermove', onMove);
    window.addEventListener('pointerup', onUp);
    window.addEventListener('pointercancel', onUp);
  }, [previewMode, previewOffset, persistAnchor]);

  const handleResetPosition = useCallback(async () => {
    const defaultAnchor = { centerX: null, y: null, dockedTop: true };
    persistAnchor(defaultAnchor);
    setPreviewOffset({ x: 0, y: 0 });
    if (!previewMode && isTauri()) {
      await applyTauriBounds(720, 382, defaultAnchor);
    }
    showToast('Позиция: верхний центр');
  }, [previewMode, applyTauriBounds, persistAnchor, showToast]);

  const handleToggleTab = useCallback((tabId) => {
    const exists = config.enabledTabs.includes(tabId);
    if (exists && config.enabledTabs.length <= 1) {
      showToast('Нужна хотя бы одна вкладка');
      return;
    }
    const rawNext = exists
      ? config.enabledTabs.filter((id) => id !== tabId)
      : [...config.enabledTabs, tabId];
    const orderedNext = ISLAND_TABS.map((t) => t.id).filter((id) => rawNext.includes(id));
    persistConfig({ ...config, enabledTabs: orderedNext });
  }, [config, persistConfig, showToast]);

  const handleToggleMainModule = useCallback((moduleKey) => {
    persistConfig({
      ...config,
      mainModules: {
        ...config.mainModules,
        [moduleKey]: !config.mainModules[moduleKey],
      },
    });
  }, [config, persistConfig]);

  const handleToggleQuickAction = useCallback((actionId) => {
    const current = Array.isArray(config.quickActions) ? config.quickActions : DEFAULT_ISLAND_CONFIG.quickActions;
    const exists = current.includes(actionId);
    const nextActions = exists
      ? current.filter((id) => id !== actionId)
      : [...current, actionId];
    persistConfig({ ...config, quickActions: nextActions });
  }, [config, persistConfig]);

  const handleResetQuickActions = useCallback(() => {
    persistConfig({ ...config, quickActions: DEFAULT_ISLAND_CONFIG.quickActions });
    showToast('Быстрые команды сброшены');
  }, [config, persistConfig, showToast]);

  const handleResetConfig = useCallback(async () => {
    persistConfig(DEFAULT_ISLAND_CONFIG);
    await handleResetPosition();
    showToast('Настройки сброшены');
  }, [persistConfig, handleResetPosition, showToast]);

  const handleDisableIsland = async () => {
    if (shrinkTimerRef.current) {
      clearTimeout(shrinkTimerRef.current);
      shrinkTimerRef.current = null;
    }
    setPhase('collapsed');
    setShowSettings(false);
    if (previewMode && onClosePreview) {
      onClosePreview();
      return;
    }
    if (isTauri()) {
      try {
        const { invoke } = await import('@tauri-apps/api/core');
        await invoke('set_island_visible', { visible: false });
      } catch {
        // Ignore
      }
    }
  };

  const handleOpenMainWindow = async () => {
    if (isTauri()) {
      try {
        const { invoke } = await import('@tauri-apps/api/core');
        await invoke('show_main_window');
      } catch {
        // Ignore
      }
    }
  };

  const handleQuickCmdSubmit = async (e) => {
    e.preventDefault();
    const cmd = quickCmd.trim();
    if (!cmd) return;
    setQuickCmd('');
    try {
      await apiPost('/api/commands/execute', { command: cmd });
      showToast(`Отправлено: ${cmd}`);
    } catch {
      sendChatMessage(cmd);
      showToast('Отправлено в чат');
    }
  };

  const handleChatSubmit = (e) => {
    e.preventDefault();
    const text = chatInput.trim();
    if (!text) return;
    sendChatMessage(text);
    setChatInput('');
  };

  const handleMediaAction = async (action, extra = {}) => {
    try {
      const res = await apiPost('/api/media/control', { action, ...extra });
      if (typeof res.volume === 'number') setVolume(res.volume);
      if (typeof res.muted === 'boolean') setMuted(res.muted);
    } catch {
      showToast('Бэкенд недоступен');
    }
  };

  const handleSystemAction = async (action, label) => {
    try {
      const res = await apiPost('/api/system/quick-action', { action });
      showToast(res?.content || label || 'Выполнено');
    } catch {
      showToast('Ошибка действия');
    }
  };

  const handleExecuteProtocol = async (proto) => {
    try {
      await apiPost('/api/protocols/execute', { protocol_id: proto.id });
      showToast(`Протокол: ${proto.name || proto.id}`);
    } catch {
      showToast('Ошибка запуска протокола');
    }
  };

  const applyTextTransform = (fn) => {
    const transformed = fn(textUtilInput);
    setTextUtilInput(transformed);
    if (navigator.clipboard?.writeText && transformed) {
      navigator.clipboard.writeText(transformed).catch(() => {});
    }
    showToast('Текст преобразован');
  };

  const filteredProtocols = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return protocols;
    return protocols.filter((p) =>
      String(p.name || p.id || '').toLowerCase().includes(q)
    );
  }, [protocols, searchQuery]);

  const allQuickActions = useMemo(() => {
    const list = [];
    const seenIds = new Set();
    const pushUnique = (item) => {
      if (seenIds.has(item.id)) return;
      seenIds.add(item.id);
      list.push(item);
    };

    for (const sys of SYSTEM_QUICK_ACTIONS) {
      pushUnique({ ...sys, kind: 'system' });
    }

    const rawCommands = catalogCommands.length > 0 ? catalogCommands : FALLBACK_COMMAND_CATALOG;
    for (const entry of rawCommands) {
      const cmdId = String(entry.id || '').trim();
      const cat = String(entry.category || 'system');
      if (!cmdId || DUPLICATE_SYSTEM_CMD_IDS.has(cmdId)) continue;
      if (cmdId.startsWith('protocol_') || cat === 'protocols') continue;

      const phrase = String((entry.commands && entry.commands[0]) || entry.example || '').trim();
      if (!phrase) continue;
      const needsArg = phrase.includes('<');
      const cleanPrefix = phrase.replace(/<[^>]*>/g, '').replace(/\s+/g, ' ').trim();
      pushUnique({
        id: `cmd:${cmdId}`,
        kind: 'command',
        cmd: phrase,
        cleanPrefix,
        needsArg,
        label: entry.name || cleanPrefix || cmdId,
        sub: needsArg ? `${CATEGORY_LABELS[cat] || 'Команда'} · ввод` : (CATEGORY_LABELS[cat] || 'Команда'),
        icon: pickCommandIcon(cmdId, cat),
        searchKey: `${entry.name || ''} ${phrase} ${cmdId} ${(entry.commands || []).join(' ')}`.toLowerCase(),
      });
    }

    return list;
  }, [catalogCommands]);

  const quickActionsById = useMemo(() => {
    const map = new Map();
    for (const item of allQuickActions) {
      map.set(item.id, item);
    }
    return map;
  }, [allQuickActions]);

  const selectedQuickActions = useMemo(() => {
    const selectedIds = Array.isArray(config.quickActions)
      ? config.quickActions
      : DEFAULT_ISLAND_CONFIG.quickActions;
    return selectedIds
      .map((id) => quickActionsById.get(id))
      .filter(Boolean);
  }, [config.quickActions, quickActionsById]);

  const filteredQuickCatalog = useMemo(() => {
    const q = actionSearch.trim().toLowerCase();
    if (!q) return allQuickActions;
    return allQuickActions.filter((item) =>
      `${item.label} ${item.sub || ''} ${item.searchKey || ''}`.toLowerCase().includes(q)
    );
  }, [allQuickActions, actionSearch]);

  const handleRunQuickItem = async (item) => {
    if (item.kind === 'system') {
      await handleSystemAction(item.action, item.label);
      return;
    }
    if (item.needsArg) {
      const nextText = `${item.cleanPrefix} `;
      setShowSettings(false);
      setActiveTab('main');
      setQuickCmd(nextText);
      requestAnimationFrame(() => quickCmdInputRef.current?.focus());
      showToast(`Допиши параметр: ${item.cleanPrefix}`);
      return;
    }
    try {
      await apiPost('/api/commands/execute', { command: item.cmd });
      showToast(item.label);
    } catch {
      sendChatMessage(item.cmd);
      showToast(`Отправлено: ${item.cmd}`);
    }
  };

  const cpuPct = Math.round(telemetry?.cpu_percent ?? telemetry?.cpu ?? 0);
  const ramPct = Math.round(telemetry?.ram_percent ?? telemetry?.memory_percent ?? 0);

  const collapsedLabel = useMemo(() => {
    if (toastText) return toastText;
    if (status === 'listen') return voskText || 'Слушаю...';
    if (status === 'think') return lastTranscript ? `«${lastTranscript}»` : 'Анализирую...';
    if (status === 'speak') return currentChunk || lastResponse || 'Отвечаю...';
    if (!connected) return 'Офлайн';
    return assistantName || 'Kirieshcka';
  }, [toastText, status, voskText, lastTranscript, currentChunk, lastResponse, connected, assistantName]);

  const isFloating = !anchorPos.dockedTop;
  const hasLeftMain = config.mainModules.voice || config.mainModules.media;
  const hasRightMain = config.mainModules.actions;

  const shellClasses = [
    'island-shell',
    isExpandedVisual ? 'expanded' : 'collapsed',
    isClosing ? 'closing' : '',
    isFloating ? 'floating' : '',
    !isExpandedVisual && hasNotchActivity ? 'has-activity' : '',
    `status-${connected ? status : 'offline'}`,
  ]
    .filter(Boolean)
    .join(' ');

  const viewportStyle = previewMode && (previewOffset.x !== 0 || previewOffset.y !== 0)
    ? { transform: `translate(${previewOffset.x}px, ${previewOffset.y}px)` }
    : undefined;

  return (
    <div
      className={`island-viewport ${previewMode ? 'preview-overlay' : ''}`}
      style={viewportStyle}
    >
      <div className={shellClasses} data-testid="dynamic-island-shell">
        <div className="island-aurora-bar" />

        <div
          className="island-collapsed-bar"
          onPointerDown={(e) => beginPointerDrag(e, { allowAnyTarget: true })}
          onClick={handleOpenIsland}
          role="button"
          tabIndex={0}
          aria-label="Открыть Dynamic Island"
          aria-hidden={isExpandedVisual}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') handleOpenIsland();
          }}
        >
          <div className="island-collapsed-left">
            <span className={`island-orb ${connected ? status : 'offline'}`} />
            {(status === 'listen' || status === 'speak') && (
              <span className={`island-eq ${status}`} aria-hidden="true">
                <span />
                <span />
                <span />
                <span />
                <span />
              </span>
            )}
            <span className="island-collapsed-text">{collapsedLabel}</span>
          </div>

          <div className="island-collapsed-right">
            {timerRunning && (
              <span className="island-pill-badge timer">{formatTimer(timerSeconds)}</span>
            )}
            {!timerRunning && connected && (
              <span className="island-pill-badge">{cpuPct}%</span>
            )}
            <span className="island-clock">{clock}</span>
          </div>
        </div>

        {showExpandedDom && (
          <div className={`island-expanded-wrap ${isClosing ? 'closing' : ''}`}>
            <header
              className="island-header"
              onPointerDown={(e) => beginPointerDrag(e)}
            >
              <div className="island-tabs" role="tablist">
                <div
                  className="island-tab-indicator"
                  style={{
                    width: `${indicatorStyle.width}px`,
                    transform: `translateX(${indicatorStyle.x}px)`,
                    opacity: showSettings ? 0.35 : 1,
                  }}
                />
                {visibleTabs.map((tab) => (
                  <button
                    key={tab.id}
                    ref={(node) => {
                      tabRefs.current[tab.id] = node;
                    }}
                    type="button"
                    role="tab"
                    aria-selected={!showSettings && activeTab === tab.id}
                    className={`island-tab-btn ${!showSettings && activeTab === tab.id ? 'active' : ''}`}
                    onClick={() => {
                      setShowSettings(false);
                      setActiveTab(tab.id);
                    }}
                  >
                    <Icon name={tab.icon} />
                    <span>{tab.label}</span>
                  </button>
                ))}
              </div>

              <div
                className="island-drag-zone"
                data-testid="island-drag-handle"
                onPointerDown={(e) => beginPointerDrag(e, { allowAnyTarget: true })}
              >
                <span className="island-drag-dots" />
              </div>

              {toastText && <span className="island-toast-inline">{toastText}</span>}

              <div className="island-header-actions">
                <button
                  type="button"
                  className={`island-icon-btn ${showSettings ? 'active' : ''}`}
                  onClick={() => {
                    setShowSettings((s) => {
                      const next = !s;
                      if (next) setSettingsSection('layout');
                      return next;
                    });
                  }}
                  title="Настроить вкладки и модули"
                  aria-label="Настроить остров"
                >
                  <Icon name="set" />
                </button>
                <button
                  type="button"
                  className={`island-icon-btn ${pinned ? 'active' : ''}`}
                  onClick={() => setPinned((p) => !p)}
                  title={pinned ? 'Открепить (сворачивать при клике вне)' : 'Закрепить открытым'}
                  aria-label="Закрепить"
                >
                  <Icon name="lock" />
                </button>
                {!previewMode && (
                  <button
                    type="button"
                    className="island-icon-btn"
                    onClick={handleOpenMainWindow}
                    title="Открыть главное окно"
                    aria-label="Главное окно"
                  >
                    <Icon name="maximize" />
                  </button>
                )}
                <button
                  type="button"
                  className="island-icon-btn"
                  onClick={handleCollapseIsland}
                  title="Свернуть в челку (Esc)"
                  aria-label="Свернуть остров"
                >
                  <Icon name="minimize" />
                </button>
                <button
                  type="button"
                  className="island-icon-btn danger"
                  onClick={handleDisableIsland}
                  title="Отключить Dynamic Island"
                  aria-label="Отключить остров"
                >
                  <Icon name="power" />
                </button>
              </div>
            </header>

            <div className="island-body">
              {showSettings ? (
                <div className="island-tab-panel" key="settings">
                  <div className="island-settings-subtabs">
                    <button
                      type="button"
                      className={`island-settings-subtab ${settingsSection === 'layout' ? 'active' : ''}`}
                      onClick={() => setSettingsSection('layout')}
                    >
                      Вкладки и блоки
                    </button>
                    <button
                      type="button"
                      className={`island-settings-subtab ${settingsSection === 'actions' ? 'active' : ''}`}
                      onClick={() => setSettingsSection('actions')}
                    >
                      Быстрые команды ({selectedQuickActions.length})
                    </button>
                  </div>

                  {settingsSection === 'layout' ? (
                    <div className="island-settings-grid">
                      <div className="island-card island-stagger" style={{ '--i': 0 }}>
                        <div className="island-card-title">
                          <span>Вкладки островка</span>
                          <span>{visibleTabs.length}/{ISLAND_TABS.length}</span>
                        </div>
                        <div className="island-toggle-grid">
                          {ISLAND_TABS.map((tab) => {
                            const on = config.enabledTabs.includes(tab.id);
                            return (
                              <button
                                key={tab.id}
                                type="button"
                                aria-pressed={on}
                                className={`island-toggle-chip ${on ? 'active' : ''}`}
                                onClick={() => handleToggleTab(tab.id)}
                              >
                                <span>{tab.label}</span>
                                <span className="island-toggle-dot" />
                              </button>
                            );
                          })}
                        </div>
                        <div className="island-pos-hint" style={{ marginTop: 'auto' }}>
                          Убери лишние вкладки или верни обратно в любой момент.
                        </div>
                      </div>

                      <div className="island-card island-stagger" style={{ '--i': 1 }}>
                        <div className="island-card-title">
                          <span>Блоки «Главное»</span>
                          <span>Модули</span>
                        </div>
                        <div className="island-toggle-grid">
                          {[
                            { key: 'voice', label: 'Голос и ввод' },
                            { key: 'media', label: 'Медиа и звук' },
                            { key: 'actions', label: 'Быстрые кнопки' },
                            { key: 'telemetry', label: 'CPU и RAM' },
                          ].map((mod) => {
                            const on = Boolean(config.mainModules[mod.key]);
                            return (
                              <button
                                key={mod.key}
                                type="button"
                                aria-pressed={on}
                                className={`island-toggle-chip ${on ? 'active' : ''}`}
                                onClick={() => handleToggleMainModule(mod.key)}
                              >
                                <span>{mod.label}</span>
                                <span className="island-toggle-dot" />
                              </button>
                            );
                          })}
                        </div>
                        <div className="island-pos-hint" style={{ marginTop: 'auto' }}>
                          Островок можно перетаскивать за шапку или чёлку.
                        </div>
                      </div>
                    </div>
                  ) : (
                    <>
                      <div className="island-cmd-form">
                        <input
                          className="island-input"
                          value={actionSearch}
                          onChange={(e) => setActionSearch(e.target.value)}
                          placeholder="Поиск по командам..."
                        />
                        <button type="button" className="island-chip" onClick={handleResetQuickActions}>
                          По умолчанию
                        </button>
                      </div>
                      <div className="island-commands-picker">
                        {filteredQuickCatalog.map((item) => {
                          const activeList = Array.isArray(config.quickActions)
                            ? config.quickActions
                            : DEFAULT_ISLAND_CONFIG.quickActions;
                          const on = activeList.includes(item.id);
                          return (
                            <button
                              key={item.id}
                              type="button"
                              aria-pressed={on}
                              className={`island-toggle-chip ${on ? 'active' : ''}`}
                              onClick={() => handleToggleQuickAction(item.id)}
                            >
                              <div className="island-cmd-pick-meta">
                                <span className="island-cmd-pick-name">{item.label}</span>
                                <span className="island-cmd-pick-sub">{item.sub}</span>
                              </div>
                              <span className="island-toggle-dot" />
                            </button>
                          );
                        })}
                        {filteredQuickCatalog.length === 0 && (
                          <div className="island-pos-hint" style={{ gridColumn: '1 / -1', padding: '8px' }}>
                            Команды по запросу не найдены.
                          </div>
                        )}
                      </div>
                    </>
                  )}

                  <div className="island-settings-footer island-stagger" style={{ '--i': 2 }}>
                    <span className="island-pos-hint">
                      Позиция: {anchorPos.dockedTop && anchorPos.centerX === null ? 'верхний центр' : anchorPos.dockedTop ? 'приклеен к верху' : 'свободная'}
                    </span>
                    <div style={{ display: 'flex', gap: '6px' }}>
                      <button type="button" className="island-chip" onClick={handleResetPosition}>
                        В центр верха
                      </button>
                      <button type="button" className="island-chip" onClick={handleResetConfig}>
                        Сбросить всё
                      </button>
                      <button
                        type="button"
                        className="island-btn"
                        onClick={() => setShowSettings(false)}
                      >
                        Готово
                      </button>
                    </div>
                  </div>
                </div>
              ) : (
                <>
              {activeTab === 'main' && (
                <div className="island-tab-panel" key="main">
                  {(hasLeftMain || hasRightMain) ? (
                  <div className={`island-main-grid ${(!hasLeftMain || !hasRightMain) ? 'single-col' : ''}`}>
                    {/* Left: Voice + Quick Command + Media */}
                    {hasLeftMain && (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', minHeight: 0 }}>
                      {config.mainModules.voice && (
                      <div className="island-card island-stagger" style={{ '--i': 0 }}>
                        <div className="island-voice-row">
                          <button
                            type="button"
                            className={`island-mic-btn ${status === 'listen' ? 'listening' : ''}`}
                            onClick={() => (status === 'listen' ? stopVoice() : startVoice())}
                            title={status === 'listen' ? 'Остановить запись' : 'Голосовая команда'}
                            aria-label="Голосовой ввод"
                          >
                            <Icon name="mic" />
                          </button>
                          <div className="island-voice-info">
                            <div className="island-voice-state">
                              {connected ? STATUS_LABELS[status] || 'Готов' : 'Ядро отключено'}
                            </div>
                            <div className="island-voice-sub">
                              {voskText || currentChunk || lastResponse || lastTranscript || 'Нажми микрофон или введи команду'}
                            </div>
                          </div>
                          {status === 'speak' && (
                            <button
                              type="button"
                              className="island-btn"
                              onClick={stopTts}
                              title="Заткнуть TTS"
                            >
                              Стоп
                            </button>
                          )}
                        </div>
                        <form className="island-cmd-form" onSubmit={handleQuickCmdSubmit}>
                          <input
                            ref={quickCmdInputRef}
                            className="island-input"
                            value={quickCmd}
                            onChange={(e) => setQuickCmd(e.target.value)}
                            placeholder="Команда или вопрос..."
                          />
                          <button type="submit" className="island-btn" aria-label="Выполнить">
                            <Icon name="send" />
                          </button>
                        </form>
                      </div>
                      )}

                      {config.mainModules.media && (
                      <div className="island-card island-stagger" style={{ '--i': 1 }}>
                        <div className="island-card-title">
                          <span>Медиа и Звук</span>
                          <span>{muted ? 'MUTE' : `${volume}%`}</span>
                        </div>
                        <div className="island-media-controls">
                          <div className="island-media-btns">
                            <button
                              type="button"
                              className="island-btn"
                              onClick={() => handleMediaAction('prev_track')}
                              title="Предыдущий трек"
                            >
                              ⏮
                            </button>
                            <button
                              type="button"
                              className="island-btn"
                              onClick={() => handleMediaAction('play_pause')}
                              title="Пауза / Плей"
                            >
                              ⏯
                            </button>
                            <button
                              type="button"
                              className="island-btn"
                              onClick={() => handleMediaAction('next_track')}
                              title="Следующий трек"
                            >
                              ⏭
                            </button>
                          </div>
                          <button
                            type="button"
                            className="island-btn"
                            onClick={() => handleMediaAction('toggle_mute')}
                            title="Выкл / Вкл звук"
                          >
                            <Icon name="vol" />
                            <span>{muted ? 'Вкл' : 'Mute'}</span>
                          </button>
                        </div>
                        <div className="island-vol-row">
                          <input
                            type="range"
                            min={0}
                            max={100}
                            value={volume}
                            onChange={(e) => {
                              const val = Number(e.target.value);
                              setVolume(val);
                              handleMediaAction('set_volume', { level: val });
                            }}
                            style={{ '--v': `${volume}%` }}
                            className="island-vol-slider"
                            aria-label="Громкость"
                          />
                          <span className="island-vol-val">{volume}%</span>
                        </div>
                      </div>
                      )}
                    </div>
                    )}

                    {/* Right: Quick Action Tiles */}
                    {hasRightMain && (
                    <div className="island-card island-stagger" style={{ '--i': 2 }}>
                      <div className="island-card-title">
                        <span>Быстрые действия</span>
                        <button
                          type="button"
                          className="island-card-link"
                          onClick={() => {
                            setSettingsSection('actions');
                            setShowSettings(true);
                          }}
                        >
                          Настроить
                        </button>
                      </div>
                      <div className="island-tiles-grid">
                        {selectedQuickActions.map((item) => (
                          <button
                            key={item.id}
                            type="button"
                            className="island-tile"
                            onClick={() => handleRunQuickItem(item)}
                          >
                            <Icon name={item.icon || 'cmd'} />
                            <span>{item.label}</span>
                          </button>
                        ))}
                        {selectedQuickActions.length === 0 && (
                          <button
                            type="button"
                            className="island-tile"
                            style={{ gridColumn: '1 / -1', justifyContent: 'center' }}
                            onClick={() => {
                              setSettingsSection('actions');
                              setShowSettings(true);
                            }}
                          >
                            <Icon name="plus" />
                            <span>Добавить быстрые команды</span>
                          </button>
                        )}
                      </div>
                    </div>
                    )}
                  </div>
                  ) : (
                    <div className="island-card" style={{ alignItems: 'center', justifyContent: 'center', flex: 1 }}>
                      <span className="island-pos-hint">Все блоки «Главного» скрыты. Открой шестерёнку сверху, чтобы включить нужные.</span>
                    </div>
                  )}

                  {config.mainModules.telemetry && (
                  <div className="island-telemetry-bar island-stagger" style={{ '--i': 3 }}>
                    <div className="island-telemetry-metric">
                      <span>CPU {cpuPct}%</span>
                      <span className="island-mini-bar">
                        <i style={{ width: `${Math.min(100, cpuPct)}%` }} />
                      </span>
                    </div>
                    <div className="island-telemetry-metric">
                      <span>RAM {ramPct}%</span>
                      <span className="island-mini-bar">
                        <i style={{ width: `${Math.min(100, ramPct)}%` }} />
                      </span>
                    </div>
                    <div className="island-telemetry-metric">
                      <span>{connected ? 'Ядро: Online' : 'Ядро: Offline'}</span>
                    </div>
                  </div>
                  )}
                </div>
              )}

              {activeTab === 'protocols' && (
                <div className="island-tab-panel" key="protocols">
                  <div className="island-cmd-form">
                    <input
                      className="island-input"
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      placeholder="Поиск по протоколам..."
                    />
                    <button type="button" className="island-btn" onClick={refreshPanelData}>
                      <Icon name="refresh" />
                    </button>
                  </div>
                  <div className="island-scroll-grid">
                    {filteredProtocols.map((proto, idx) => (
                      <button
                        key={`proto-${proto.id}`}
                        type="button"
                        className="island-item-pill island-stagger"
                        style={{ '--i': Math.min(idx, 8) }}
                        onClick={() => handleExecuteProtocol(proto)}
                      >
                        <span>⚡ {proto.name || proto.id}</span>
                        <span className="island-item-sub">Протокол</span>
                      </button>
                    ))}
                    {filteredProtocols.length === 0 && (
                      <div style={{ gridColumn: '1 / -1', color: 'var(--tx-dim)', fontSize: '12px', padding: '12px' }}>
                        Протоколы не найдены или бэкенд не запущен.
                      </div>
                    )}
                  </div>
                </div>
              )}

              {activeTab === 'chat' && (
                <div className="island-tab-panel" key="chat">
                  <div className="island-chat-list">
                    {messages.slice(-20).map((m) => (
                      <div key={m.id} className={`island-msg ${m.sender === 'user' ? 'user' : 'assistant'}`}>
                        {m.text}
                      </div>
                    ))}
                    {isStreaming && currentChunk && (
                      <div className="island-msg assistant">{currentChunk}</div>
                    )}
                    <div ref={chatEndRef} />
                  </div>
                  <form className="island-cmd-form" onSubmit={handleChatSubmit}>
                    <input
                      className="island-input"
                      value={chatInput}
                      onChange={(e) => setChatInput(e.target.value)}
                      placeholder="Написать Ollama..."
                    />
                    <button type="submit" className="island-btn">
                      <Icon name="send" />
                    </button>
                    <button
                      type="button"
                      className="island-btn"
                      onClick={clearChatMessages}
                      title="Очистить чат"
                    >
                      <Icon name="trash" />
                    </button>
                  </form>
                </div>
              )}

              {activeTab === 'tools' && (
                <div className="island-tab-panel" key="tools">
                  <div className="island-tools-grid">
                    <div className="island-card island-stagger" style={{ '--i': 0 }}>
                      <div className="island-card-title">
                        <span>Заметка и текст</span>
                        <button
                          type="button"
                          className="island-chip"
                          onClick={() => setNoteText('')}
                        >
                          Очистить
                        </button>
                      </div>
                      <textarea
                        className="island-textarea"
                        value={noteText}
                        onChange={(e) => setNoteText(e.target.value)}
                        placeholder="Быстрые заметки (автосохранение)..."
                      />
                      <input
                        className="island-input"
                        value={textUtilInput}
                        onChange={(e) => setTextUtilInput(e.target.value)}
                        placeholder="Текст для фикса раскладки / JSON..."
                      />
                      <div className="island-chip-row">
                        <button
                          type="button"
                          className="island-chip"
                          onClick={() => applyTextTransform(fixKeyboardLayout)}
                        >
                          Раскладка EN↔RU
                        </button>
                        <button
                          type="button"
                          className="island-chip"
                          onClick={() => applyTextTransform((t) => t.toUpperCase())}
                        >
                          ВЕРХНИЙ
                        </button>
                        <button
                          type="button"
                          className="island-chip"
                          onClick={() => applyTextTransform((t) => t.replace(/\s+/g, ' ').trim())}
                        >
                          Пробелы
                        </button>
                        <button
                          type="button"
                          className="island-chip"
                          onClick={() =>
                            applyTextTransform((t) => {
                              try {
                                return JSON.stringify(JSON.parse(t), null, 2);
                              } catch {
                                return t;
                              }
                            })
                          }
                        >
                          JSON
                        </button>
                      </div>
                    </div>

                    <div className="island-card island-stagger" style={{ '--i': 1 }}>
                      <div className="island-card-title">
                        <span>Таймер фокуса</span>
                        <span>{timerRunning ? 'Идет' : 'Пауза'}</span>
                      </div>
                      <div className="island-timer-display">{formatTimer(timerSeconds)}</div>
                      <div className="island-chip-row" style={{ justifyContent: 'center' }}>
                        {[5, 10, 15, 25, 45].map((mins) => (
                          <button
                            key={mins}
                            type="button"
                            className="island-chip"
                            onClick={() => {
                              setTimerRunning(false);
                              setTimerSeconds(mins * 60);
                            }}
                          >
                            {mins}м
                          </button>
                        ))}
                      </div>
                      <div style={{ display: 'flex', gap: '8px', marginTop: 'auto' }}>
                        <button
                          type="button"
                          className="island-btn"
                          style={{ flex: 1 }}
                          onClick={() => {
                            if (timerSeconds === 0) setTimerSeconds(5 * 60);
                            setTimerRunning((r) => !r);
                          }}
                        >
                          {timerRunning ? 'Пауза' : 'Старт'}
                        </button>
                        <button
                          type="button"
                          className="island-btn"
                          onClick={() => {
                            setTimerRunning(false);
                            setTimerSeconds(5 * 60);
                          }}
                        >
                          Сброс
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              )}
                </>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
