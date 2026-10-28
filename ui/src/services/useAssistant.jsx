import { useState, useEffect } from 'react';
import { assistantSocket } from './assistantSocket';

export function useAssistant() {
  const [state, setState] = useState(assistantSocket.state);
  const [messages, setMessages] = useState(() => assistantSocket.getMessages());

  useEffect(() => {
    assistantSocket.connect();
    const unsubState = assistantSocket.on('state_change', (nextState) => {
      setState(nextState);
    });
    const unsubMsgs = assistantSocket.on('messages_change', (nextMsgs) => {
      setMessages([...nextMsgs]);
    });
    return () => {
      unsubState();
      unsubMsgs();
    };
  }, []);

  return {
    ...state,
    messages,
    sendChatMessage: (text, thinking = false) => assistantSocket.sendChatMessage(text, thinking),
    clearChatMessages: () => assistantSocket.clearChatMessages(),
    startVoice: () => assistantSocket.startVoice(),
    stopVoice: () => assistantSocket.stopVoice(),
    toggleWakeWord: (enabled) => assistantSocket.toggleWakeWord(enabled),
    stopTts: () => assistantSocket.stopTts(),
    requestTelemetry: () => assistantSocket.requestTelemetry(),
  };
}
