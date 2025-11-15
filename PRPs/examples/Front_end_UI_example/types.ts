
export interface FileAttachment {
  name: string;
  type: string; // MIME type
  content: string; // base64 data URL
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'model';
  text: string;
  files?: FileAttachment[];
}

export interface ChatSession {
  id: string;
  title: string;
  messages: ChatMessage[];
}
