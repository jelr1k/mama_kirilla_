import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useAssistant } from './useAssistant';
import { assistantSocket } from './assistantSocket';

describe('useAssistant hook', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('connects to assistantSocket on mount and cleans up listeners on unmount', () => {
    const connectSpy = vi.spyOn(assistantSocket, 'connect').mockResolvedValue();
    const onSpy = vi.spyOn(assistantSocket, 'on');

    const { unmount } = renderHook(() => useAssistant());

    expect(connectSpy).toHaveBeenCalledTimes(1);
    expect(onSpy).toHaveBeenCalledWith('state_change', expect.any(Function));
    expect(onSpy).toHaveBeenCalledWith('messages_change', expect.any(Function));

    unmount();
  });

  it('reacts to state_change and messages_change events', () => {
    vi.spyOn(assistantSocket, 'connect').mockResolvedValue();

    const { result } = renderHook(() => useAssistant());

    act(() => {
      assistantSocket._emit('state_change', {
        ...assistantSocket.state,
        status: 'speak',
        lastResponse: 'Привет, мир!',
      });
    });

    expect(result.current.status).toBe('speak');
    expect(result.current.lastResponse).toBe('Привет, мир!');

    const newMsgs = [{ id: 99, sender: 'user', text: 'Новое сообщение', time: '12:00' }];
    act(() => {
      assistantSocket._emit('messages_change', newMsgs);
    });

    expect(result.current.messages).toHaveLength(1);
    expect(result.current.messages[0].text).toBe('Новое сообщение');
  });

  it('proxies command actions directly to assistantSocket methods', () => {
    vi.spyOn(assistantSocket, 'connect').mockResolvedValue();
    const sendChatSpy = vi.spyOn(assistantSocket, 'sendChatMessage').mockReturnValue(true);
    const clearChatSpy = vi.spyOn(assistantSocket, 'clearChatMessages').mockImplementation(() => {});
    const startVoiceSpy = vi.spyOn(assistantSocket, 'startVoice').mockReturnValue(true);
    const stopVoiceSpy = vi.spyOn(assistantSocket, 'stopVoice').mockReturnValue(true);
    const toggleWakeSpy = vi.spyOn(assistantSocket, 'toggleWakeWord').mockReturnValue(true);
    const stopTtsSpy = vi.spyOn(assistantSocket, 'stopTts').mockReturnValue(true);
    const telemetrySpy = vi.spyOn(assistantSocket, 'requestTelemetry').mockReturnValue(true);

    const { result } = renderHook(() => useAssistant());

    result.current.sendChatMessage('текст', true);
    expect(sendChatSpy).toHaveBeenCalledWith('текст', true);

    result.current.clearChatMessages();
    expect(clearChatSpy).toHaveBeenCalledTimes(1);

    result.current.startVoice();
    expect(startVoiceSpy).toHaveBeenCalledTimes(1);

    result.current.stopVoice();
    expect(stopVoiceSpy).toHaveBeenCalledTimes(1);

    result.current.toggleWakeWord(false);
    expect(toggleWakeSpy).toHaveBeenCalledWith(false);

    result.current.stopTts();
    expect(stopTtsSpy).toHaveBeenCalledTimes(1);

    result.current.requestTelemetry();
    expect(telemetrySpy).toHaveBeenCalledTimes(1);
  });
});
