
export type ChatProvider = 'fastapi' | 'gemini';

export interface FileAttachment {
  name: string;
  type: string; // MIME type
  content: string; // base64 data URL
}

export interface Citation {
  source: string;
  chunkId?: string;
  score?: number;
}

export interface ChatResponsePayload {
  message: string;
  citations?: Citation[];
}

export interface TransportRequest {
  text: string;
  files: File[];
}

export interface ChatTransport {
  provider: ChatProvider;
  sendMessage: (request: TransportRequest) => Promise<ChatResponsePayload>;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'model';
  text: string;
  citations?: Citation[];
  files?: FileAttachment[];
}

export interface ChatSession {
  id: string;
  title: string;
  messages: ChatMessage[];
}
