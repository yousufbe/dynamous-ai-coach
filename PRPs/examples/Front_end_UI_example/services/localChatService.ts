import type {
  ChatResponsePayload,
  ChatTransport,
  Citation,
  TransportRequest,
} from '../types';

interface LocalChatServiceConfig {
  baseUrl: string;
}

interface ChatApiResponse {
  answer: string;
  citations?: Array<{
    source: string;
    chunk_id?: string;
    score?: number;
  }>;
}

const mapCitations = (citations: ChatApiResponse['citations']): Citation[] | undefined => {
  if (!citations || citations.length === 0) {
    return undefined;
  }
  return citations.map((citation) => ({
    source: citation.source,
    chunkId: citation.chunk_id,
    score: citation.score,
  }));
};

const buildError = (message: string, status?: number): Error => {
  const error = new Error(message);
  if (status) {
    (error as Error & { status?: number }).status = status;
  }
  return error;
};

export const createLocalChatTransport = (config: LocalChatServiceConfig): ChatTransport => {
  const sendMessage = async (request: TransportRequest): Promise<ChatResponsePayload> => {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 30000);
    try {
      const response = await fetch(`${config.baseUrl}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query: request.text }),
        signal: controller.signal,
      });
      if (!response.ok) {
        throw buildError(`Backend returned ${response.status}`, response.status);
      }
      const data = (await response.json()) as ChatApiResponse;
      return {
        message: data.answer ?? 'The assistant did not return a response.',
        citations: mapCitations(data.citations),
      };
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
        throw buildError('Request timed out');
      }
      throw error instanceof Error ? error : buildError('Unknown error calling backend');
    } finally {
      clearTimeout(timeout);
    }
  };

  return {
    provider: 'fastapi',
    sendMessage,
  };
};
