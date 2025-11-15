
import { GoogleGenAI } from "@google/genai";
import type { ChatResponsePayload, ChatTransport, TransportRequest } from '../types';
import { fileToGenerativePart } from '../utils/fileUtils';

const resolveApiKey = (): string => {
  const key = (import.meta.env.VITE_GEMINI_API_KEY as string | undefined) ?? (import.meta.env.API_KEY as string | undefined);
  if (!key) {
    throw new Error("VITE_GEMINI_API_KEY environment variable not set.");
  }
  return key;
};

const createClient = (): GoogleGenAI => {
  const apiKey = resolveApiKey();
  return new GoogleGenAI({ apiKey });
};

const buildResponse = (text: string | undefined): ChatResponsePayload => ({
  message: text ?? 'The Gemini service did not return a response.',
});

export const createGeminiChatTransport = (): ChatTransport => {
  const ai = createClient();

  const sendMessage = async (request: TransportRequest): Promise<ChatResponsePayload> => {
    const modelIdentifier = 'gemini-2.5-flash';
    if (request.files.length === 0) {
      const response = await ai.models.generateContent({
        model: modelIdentifier,
        contents: request.text,
      });
      return buildResponse(response.text);
    }

    const fileParts = await Promise.all(
      request.files.map((file) => fileToGenerativePart(file)),
    );
    const parts = [...fileParts, { text: request.text }];
    const response = await ai.models.generateContent({
      model: modelIdentifier,
      contents: { parts },
    });
    return buildResponse(response.text);
  };

  return {
    provider: 'gemini',
    sendMessage,
  };
};
