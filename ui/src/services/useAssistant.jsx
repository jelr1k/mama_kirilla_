import { useState, useEffect } from 'react';
import { assistantSocket } from './assistantSocket';

export function useAssistant() {
  const [state, setState] = useState(assistantSocket.state);

  useEffect(() => {
    assistantSocket.connect();
    const unsubscribe = assistantSocket.on('state_change', (nextState) => {
      setState(nextState);
    });
    return () => {
      unsubscribe();
    };
  }, []);

  return {
    ...state,
    sendChatMessage: (text, thinking = false) => assistantSocket.sendChatMessage(text, thinking),
    startVoice: () => assistantSocket.startVoice(),
    stopVoice: () => assistantSocket.stopVoice(),
    toggleWakeWord: (enabled) => assistantSocket.toggleWakeWord(enabled),
    stopTts: () => assistantSocket.stopTts(),
    requestTelemetry: () => assistantSocket.requestTelemetry(),
  };
}
