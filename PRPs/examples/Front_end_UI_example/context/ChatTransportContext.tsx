import { createContext, useContext, useMemo } from 'react';
import type { PropsWithChildren } from 'react';
import { createChatTransport } from '../services/chatTransport';
import type { ChatTransport } from '../types';

const ChatTransportContext = createContext<ChatTransport | null>(null);

export const ChatTransportProvider = ({ children }: PropsWithChildren): JSX.Element => {
  const transport = useMemo<ChatTransport>(() => createChatTransport(), []);
  return (
    <ChatTransportContext.Provider value={transport}>
      {children}
    </ChatTransportContext.Provider>
  );
};

export const useChatTransport = (): ChatTransport => {
  const transport = useContext(ChatTransportContext);
  if (!transport) {
    throw new Error('ChatTransportProvider is missing in component tree.');
  }
  return transport;
};
