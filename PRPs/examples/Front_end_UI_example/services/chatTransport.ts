import type {
  ChatProvider,
  ChatResponsePayload,
  ChatTransport,
  TransportRequest,
} from '../types';
import { createLocalChatTransport } from './localChatService';
import { createGeminiChatTransport } from './geminiService';

const DEFAULT_PROVIDER: ChatProvider = 'fastapi';

function resolveProvider(envProvider: string | undefined): ChatProvider {
  if (envProvider === 'gemini') {
    return 'gemini';
  }
  return DEFAULT_PROVIDER;
}

export const createChatTransport = (): ChatTransport => {
  const provider = resolveProvider(import.meta.env.VITE_PROVIDER as string | undefined);
  if (provider === 'gemini') {
    return createGeminiChatTransport();
  }
  const backendUrl =
    (import.meta.env.VITE_BACKEND_URL as string | undefined) ?? 'http://localhost:8030';
  return createLocalChatTransport({ baseUrl: backendUrl });
};

export type { ChatProvider, ChatResponsePayload, ChatTransport, TransportRequest };
