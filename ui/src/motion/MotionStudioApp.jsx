import React, { useState, useRef, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Icon } from '../components/Icons';
import './MotionStudio.css';
import {
  INITIAL_PROTOCOLS,
  INITIAL_COMMANDS,
  INITIAL_EVENTS,
  INITIAL_CHAT,
  DEMO_REPLIES,
} from './mockData';
import OscilloscopeCanvas from './components/OscilloscopeCanvas';
import RotaryKnob from './components/RotaryKnob';
import HardwareModule from './components/HardwareModule';
import { playClick, playSwitch } from './sfx';

const isTauri = () => Boolean(window.__TAURI_INTERNALS__);

const nowTime = () => new Date().toTimeString().slice(0, 8);

const INITIAL_ORDER = ['voice', 'gain', 'protocols', 'console', 'telemetry'];

export default function MotionStudioApp({ assistantName = 'Assistant', onSwitchToClassic }) {
  const workspaceRef = useRef(null);
  const protoTimerRef = useRef(null);

  const [listening, setListening] = useState(false);
  const [volume, setVolume] = useState(72);
  const [oscMode, setOscMode] = useState('wave'); // 'wave' | 'matrix'
  const [sfxEnabled, setSfxEnabled] = useState(true);
  const [resetTick, setResetTick] = useState(0);

  const [zOrder, setZOrder] = useState(INITIAL_ORDER);
  const [collapsed, setCollapsed] = useState({ telemetry: true });
  const [expandedId, setExpandedId] = useState(null);

  const [runningProtoId, setRunningProtoId] = useState(null);
  const [protoProgress, setProtoProgress] = useState(0);

  const [events, setEvents] = useState(INITIAL_EVENTS);
  const [messages, setMessages] = useState(INITIAL_CHAT);
  const [chatInput, setChatInput] = useState('');
  const [toasts, setToasts] = useState([]);

  const pushToast = useCallback((text) => {
    const id = `${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
    setToasts((prev) => [{ id, text }, ...prev.slice(0, 2)]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 2600);
  }, []);

  const pushEvent = useCallback((source, text) => {
    setEvents((prev) => [
      { id: `${Date.now()}-${Math.random().toString(36).slice(2, 6)}`, time: nowTime(), source, text },
      ...prev.slice(0, 14),
    ]);
  }, []);

  useEffect(() => {
    return () => {
      if (protoTimerRef.current) clearInterval(protoTimerRef.current);
    };
  }, []);

  const bringToFront = (id) => {
    setZOrder((prev) => [...prev.filter((item) => item !== id), id]);
  };

  const getZ = (id) => 10 + zOrder.indexOf(id);

  const toggleCollapse = (id) => {
    playClick(sfxEnabled, 740, 0.02);
    setCollapsed((prev) => ({ ...prev, [id]: !prev[id] }));
    if (expandedId === id) setExpandedId(null);
  };

  const toggleExpand = (id) => {
    playClick(sfxEnabled, expandedId === id ? 500 : 880, 0.028);
    setCollapsed((prev) => ({ ...prev, [id]: false }));
    setExpandedId((prev) => (prev === id ? null : id));
  };

  const handleToggleListening = () => {
    const next = !listening;
    playSwitch(sfxEnabled, next);
    setListening(next);
    pushEvent('VOICE', next ? 'AUDIO TRIGGER ARMED (SANDBOX)' : 'AUDIO TRIGGER IDLE');
    pushToast(next ? 'MIC ARMED // СЛУШАЮ ПОТОК' : 'MIC IDLE');
  };

  const handleRunProtocol = (proto) => {
    playClick(sfxEnabled, 600, 0.03);
    if (protoTimerRef.current) clearInterval(protoTimerRef.current);
    setRunningProtoId(proto.id);
    setProtoProgress(5);
    pushEvent('SEQ', `RUN ${proto.name.toUpperCase()}`);

    const stepMs = 60;
    const inc = (100 / proto.durationMs) * stepMs;
    protoTimerRef.current = setInterval(() => {
      setProtoProgress((prev) => {
        const next = prev + inc;
        if (next >= 100) {
          clearInterval(protoTimerRef.current);
          protoTimerRef.current = null;
          playSwitch(sfxEnabled, true);
          setTimeout(() => {
            setRunningProtoId(null);
            setProtoProgress(0);
          }, 280);
          pushEvent('DONE', `${proto.name.toUpperCase()} [OK]`);
          pushToast(`DONE // ${proto.name}`);
          return 100;
        }
        return next;
      });
    }, stepMs);
  };

  const handleSendChat = (text) => {
    const trimmed = (text ?? chatInput).trim();
    if (!trimmed) return;
    playClick(sfxEnabled, 780, 0.02);
    setMessages((prev) => [...prev, { id: `u-${Date.now()}`, role: 'user', text: trimmed, time: nowTime().slice(0, 5) }]);
    if (text === undefined) setChatInput('');
    pushEvent('TERM', trimmed);

    setTimeout(() => {
      const reply = DEMO_REPLIES[Math.floor(Math.random() * DEMO_REPLIES.length)];
      setMessages((prev) => [...prev, { id: `a-${Date.now()}`, role: 'assistant', text: reply, time: nowTime().slice(0, 5) }]);
    }, 300);
  };

  const handleResetDesk = () => {
    playSwitch(sfxEnabled, true);
    setExpandedId(null);
    setCollapsed({ telemetry: true });
    setResetTick((t) => t + 1);
    pushToast('DESK LAYOUT RESET');
  };

  const handleWindowAction = async (action) => {
    if (!isTauri()) {
      if (action === 'close') window.close();
      return;
    }
    try {
      const { getCurrentWindow } = await import('@tauri-apps/api/window');
      const win = getCurrentWindow();
      if (action === 'min') await win.minimize();
      if (action === 'max') await win.toggleMaximize();
      if (action === 'close') await win.hide();
    } catch {}
  };

  return (
    <div className="te-shell" data-testid="motion-studio-shell">
      {/* Top Hardware Bar */}
      <header className="te-topbar" data-tauri-drag-region>
        <div className="te-topbar-group" data-tauri-drag-region>
          <div className="te-unit-tag" data-tauri-drag-region>
            <span className={`te-status-led ${listening ? 'hot' : ''}`} />
            <span>{assistantName.toUpperCase()} // FIELD-02</span>
          </div>
          <span className="te-unit-tag" style={{ color: '#b8ff3b' }}>
            SANDBOX
          </span>
        </div>

        <div className="te-topbar-group" data-tauri-drag-region="false">
          <motion.button
            type="button"
            className="te-key"
            whileTap={{ y: 2, boxShadow: '0 1px 0 #090a0d' }}
            onClick={() => {
              playClick(sfxEnabled, 700, 0.02);
              setOscMode((m) => (m === 'wave' ? 'matrix' : 'wave'));
            }}
          >
            OSC: {oscMode.toUpperCase()}
          </motion.button>

          <motion.button
            type="button"
            className={`te-key ${sfxEnabled ? 'active' : ''}`}
            whileTap={{ y: 2, boxShadow: '0 1px 0 #090a0d' }}
            onClick={() => {
              const next = !sfxEnabled;
              setSfxEnabled(next);
              if (next) playSwitch(true, true);
            }}
          >
            SFX: {sfxEnabled ? 'ON' : 'OFF'}
          </motion.button>

          <motion.button
            type="button"
            className="te-key"
            whileTap={{ y: 2, boxShadow: '0 1px 0 #090a0d' }}
            onClick={handleResetDesk}
          >
            RESET DESK
          </motion.button>

          <motion.button
            type="button"
            className="te-key orange"
            whileTap={{ y: 2, boxShadow: '0 1px 0 #701f00' }}
            onClick={() => {
              playClick(sfxEnabled, 520, 0.03);
              onSwitchToClassic();
            }}
            data-testid="switch-to-classic-btn"
          >
            КЛАССИКА
          </motion.button>

          <button type="button" className="te-win-btn" onClick={() => handleWindowAction('min')} aria-label="Свернуть">
            <Icon name="minus" />
          </button>
          <button type="button" className="te-win-btn" onClick={() => handleWindowAction('max')} aria-label="Развернуть">
            <Icon name="square" />
          </button>
          <button type="button" className="te-win-btn close" onClick={() => handleWindowAction('close')} aria-label="Скрыть">
            <Icon name="x" />
          </button>
        </div>
      </header>

      {/* Free Draggable Workspace + Center Live Oscilloscope */}
      <div className="te-workspace" ref={workspaceRef}>
        <div className="te-center-stage">
          <div className="te-osc-housing">
            <div className="te-osc-header">
              <span>SIGNAL MONITOR // {oscMode === 'wave' ? 'DUAL HARMONIC' : 'DOT MATRIX 36x14'}</span>
              <span style={{ color: listening ? '#ff4d00' : '#9aa0ad' }}>
                {listening ? 'INPUT: LIVE' : 'INPUT: STANDBY · MOVE CURSOR'}
              </span>
            </div>
            <OscilloscopeCanvas
              listening={listening}
              volume={volume}
              mode={oscMode}
              accent="#ff4d00"
            />
          </div>
        </div>

        {/* MOD-01: Voice Trigger */}
        <HardwareModule
          id="voice"
          code="MOD-01"
          title="VOICE OSC"
          dragConstraints={workspaceRef}
          zIndex={getZ('voice')}
          onFocus={bringToFront}
          collapsed={Boolean(collapsed.voice)}
          onToggleCollapse={toggleCollapse}
          expanded={expandedId === 'voice'}
          onToggleExpand={toggleExpand}
          resetTick={resetTick}
          defaultPos={{ x: 0, y: 0 }}
          width={290}
          accentDot={listening ? '#ff4d00' : '#5d6473'}
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div className="te-well-box" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span>WAKE: ШПРОТА</span>
              <span style={{ color: listening ? '#ff4d00' : '#9aa0ad', fontWeight: 700 }}>
                {listening ? 'ARMED' : 'IDLE'}
              </span>
            </div>

            <motion.button
              type="button"
              className={`te-key ${listening ? 'orange' : ''}`}
              style={{ width: '100%', padding: '11px 12px', fontSize: 12 }}
              whileTap={{ y: 2, boxShadow: '0 1px 0 #090a0d' }}
              onClick={handleToggleListening}
            >
              <Icon name={listening ? 'mic' : 'zap'} />
              <span>{listening ? 'STOP CAPTURE' : 'ARM VOICE TRIGGER'}</span>
            </motion.button>
          </div>
        </HardwareModule>

        {/* MOD-02: Rotary Gain Knob */}
        <HardwareModule
          id="gain"
          code="MOD-02"
          title="MASTER GAIN"
          dragConstraints={workspaceRef}
          zIndex={getZ('gain')}
          onFocus={bringToFront}
          collapsed={Boolean(collapsed.gain)}
          onToggleCollapse={toggleCollapse}
          expanded={expandedId === 'gain'}
          onToggleExpand={toggleExpand}
          resetTick={resetTick}
          defaultPos={{ x: 760, y: 0 }}
          width={230}
          accentDot="#b8ff3b"
        >
          <RotaryKnob
            value={volume}
            onChange={(val) => {
              setVolume(val);
            }}
            label="MASTER VOL"
          />
        </HardwareModule>

        {/* MOD-03: Hardware Protocol Pads */}
        <HardwareModule
          id="protocols"
          code="MOD-03"
          title="PROTO DECK"
          dragConstraints={workspaceRef}
          zIndex={getZ('protocols')}
          onFocus={bringToFront}
          collapsed={Boolean(collapsed.protocols)}
          onToggleCollapse={toggleCollapse}
          expanded={expandedId === 'protocols'}
          onToggleExpand={toggleExpand}
          resetTick={resetTick}
          defaultPos={{ x: 0, y: 260 }}
          width={330}
          accentDot="#ff4d00"
        >
          <div className="te-pads" style={expandedId === 'protocols' ? { gridTemplateColumns: 'repeat(2, 1fr)', gap: 14 } : undefined}>
            {INITIAL_PROTOCOLS.map((proto) => {
              const isRunning = runningProtoId === proto.id;
              return (
                <motion.button
                  key={proto.id}
                  type="button"
                  className="te-pad"
                  whileTap={{ y: 3, boxShadow: '0 1px 0 #090a0c' }}
                  onClick={() => handleRunProtocol(proto)}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontFamily: 'var(--te-mono)', fontSize: 10, color: 'var(--te-dim)' }}>
                    <span>{proto.tag}</span>
                    <span>{isRunning ? `${Math.round(protoProgress)}%` : 'PAD'}</span>
                  </div>
                  <div style={{ fontSize: 13, fontWeight: 700, marginTop: 4 }}>{proto.name}</div>

                  <div className="te-step-leds">
                    {proto.steps.map((s, idx) => {
                      const lit = isRunning && protoProgress >= ((idx + 1) / proto.steps.length) * 100;
                      return <span key={s.id} className={`te-step-led ${lit ? 'on' : ''}`} />;
                    })}
                  </div>

                  {expandedId === 'protocols' && (
                    <div style={{ marginTop: 10, display: 'flex', flexDirection: 'column', gap: 4, fontSize: 11.5, color: 'var(--te-dim)' }}>
                      {proto.steps.map((s, i) => (
                        <div key={s.id}>0{i + 1}. {s.label} ({s.detail})</div>
                      ))}
                    </div>
                  )}

                  <motion.div
                    className="te-pad-bar"
                    style={{ background: proto.accent }}
                    animate={{ scaleX: isRunning ? protoProgress / 100 : 0 }}
                    transition={{ duration: 0.08, ease: 'linear' }}
                  />
                </motion.button>
              );
            })}
          </div>
        </HardwareModule>

        {/* MOD-04: Terminal / Commands */}
        <HardwareModule
          id="console"
          code="MOD-04"
          title="CMD TERMINAL"
          dragConstraints={workspaceRef}
          zIndex={getZ('console')}
          onFocus={bringToFront}
          collapsed={Boolean(collapsed.console)}
          onToggleCollapse={toggleCollapse}
          expanded={expandedId === 'console'}
          onToggleExpand={toggleExpand}
          resetTick={resetTick}
          defaultPos={{ x: 650, y: 250 }}
          width={340}
          accentDot="#38bdf8"
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <div className="te-well-box" style={{ maxHeight: expandedId === 'console' ? 280 : 120, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 6 }}>
              {messages.map((m) => (
                <div key={m.id} style={{ color: m.role === 'user' ? '#b8ff3b' : '#eef0f4' }}>
                  <span style={{ color: '#5d6473', marginRight: 6 }}>[{m.role === 'user' ? 'USR' : 'SYS'}]</span>
                  {m.text}
                </div>
              ))}
            </div>

            {expandedId === 'console' && (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 6 }}>
                {INITIAL_COMMANDS.map((cmd) => (
                  <motion.button
                    key={cmd.id}
                    type="button"
                    className="te-key"
                    whileTap={{ y: 2 }}
                    onClick={() => handleSendChat(cmd.phrase)}
                  >
                    {cmd.title}
                  </motion.button>
                ))}
              </div>
            )}

            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSendChat();
              }}
              style={{ display: 'flex', gap: 6 }}
            >
              <input
                type="text"
                className="te-input"
                placeholder="> команда..."
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
              />
              <motion.button
                type="submit"
                className="te-key orange"
                whileTap={{ y: 2 }}
              >
                EXEC
              </motion.button>
            </form>
          </div>
        </HardwareModule>

        {/* MOD-05: Telemetry Log */}
        <HardwareModule
          id="telemetry"
          code="MOD-05"
          title="EVENT BUS"
          dragConstraints={workspaceRef}
          zIndex={getZ('telemetry')}
          onFocus={bringToFront}
          collapsed={Boolean(collapsed.telemetry)}
          onToggleCollapse={toggleCollapse}
          expanded={expandedId === 'telemetry'}
          onToggleExpand={toggleExpand}
          resetTick={resetTick}
          defaultPos={{ x: 340, y: 0 }}
          width={360}
          accentDot="#9aa0ad"
        >
          <div className="te-well-box" style={{ maxHeight: 160, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 5 }}>
            {events.map((ev) => (
              <div key={ev.id} style={{ display: 'flex', gap: 8 }}>
                <span style={{ color: '#ff4d00' }}>{ev.source}</span>
                <span style={{ flex: 1 }}>{ev.text}</span>
                <span style={{ color: '#5d6473' }}>{ev.time}</span>
              </div>
            ))}
          </div>
        </HardwareModule>
      </div>

      {/* Hardware Toasts */}
      <div className="te-toasts">
        <AnimatePresence>
          {toasts.map((t) => (
            <motion.div
              key={t.id}
              initial={{ opacity: 0, y: 14, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 10, scale: 0.95 }}
              className="te-toast"
            >
              {t.text}
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </div>
  );
}
