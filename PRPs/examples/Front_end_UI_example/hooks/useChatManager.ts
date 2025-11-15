
import { useState, useEffect, useCallback } from 'react';
import type {
  ChatSession,
  ChatMessage,
  FileAttachment,
} from '../types';
import { useChatTransport } from '../context/ChatTransportContext';

const initialSession: ChatSession = {
  id: `session_${Date.now()}`,
  title: 'New Chat',
  messages: [],
};

interface UseChatManagerResult {
  sessions: ChatSession[];
  activeSessionId: string | null;
  activeSession: ChatSession | undefined;
  isLoading: boolean;
  createNewSession: () => void;
  setActiveSession: (id: string) => void;
  sendMessage: (text: string, files: File[]) => Promise<void>;
}

export const useChatManager = (): UseChatManagerResult => {
  const transport = useChatTransport();
  const [sessions, setSessions] = useState<ChatSession[]>(() => {
    try {
      const savedSessions = localStorage.getItem('chatSessions');
      return savedSessions ? JSON.parse(savedSessions) : [initialSession];
    } catch (error) {
      console.error('Failed to load sessions from localStorage', error);
      return [initialSession];
    }
  });

  const [activeSessionId, setActiveSessionId] = useState<string | null>(sessions[0]?.id || null);
  const [isLoading, setIsLoading] = useState<boolean>(false);

  useEffect(() => {
    try {
      localStorage.setItem('chatSessions', JSON.stringify(sessions));
    } catch (error) {
      console.error('Failed to save sessions to localStorage', error);
    }
  }, [sessions]);

  const setActiveSession = (id: string): void => {
    setActiveSessionId(id);
  };

  const createNewSession = (): void => {
    const newSession: ChatSession = {
      id: `session_${Date.now()}`,
      title: 'New Chat',
      messages: [],
    };
    setSessions(prev => [newSession, ...prev]);
    setActiveSessionId(newSession.id);
  };
  
  const updateSession = useCallback((sessionId: string, updatedMessages: ChatMessage[], newTitle?: string) => {
      setSessions(prevSessions =>
        prevSessions.map(session =>
          session.id === sessionId
            ? { ...session, title: newTitle || session.title, messages: updatedMessages }
            : session
        )
      );
  }, []);


  const sendMessage = async (text: string, files: File[]): Promise<void> => {
    if (!activeSessionId) {
      return;
    }

    setIsLoading(true);

    const fileAttachments: FileAttachment[] = await Promise.all(
      files.map(async (file) => ({
        name: file.name,
        type: file.type,
        content: await new Promise<string>((resolve) => {
          const reader = new FileReader();
          reader.onload = (event) => resolve(event.target?.result as string);
          reader.readAsDataURL(file);
        }),
      })),
    );

    const userMessage: ChatMessage = {
      id: `msg_${Date.now()}`,
      role: 'user',
      text,
      files: fileAttachments,
    };

    const activeSession = sessions.find((session) => session.id === activeSessionId);
    if (!activeSession) {
      setIsLoading(false);
      return;
    }

    const updatedMessages = [...activeSession.messages, userMessage];
    updateSession(activeSessionId, updatedMessages);

    try {
      const response = await transport.sendMessage({
        text,
        files,
      });

      const modelMessage: ChatMessage = {
        id: `msg_${Date.now() + 1}`,
        role: 'model',
        text: response.message,
        citations: response.citations,
      };

      const finalMessages = [...updatedMessages, modelMessage];

      let newTitle = activeSession.title;
      if (activeSession.messages.length === 0) {
        newTitle = text.substring(0, 30) + (text.length > 30 ? '...' : '');
      }

      updateSession(activeSessionId, finalMessages, newTitle);
    } catch (error) {
      console.error('Error generating content:', error);
      const errorMessage: ChatMessage = {
        id: `msg_${Date.now() + 1}`,
        role: 'model',
        text: 'Sorry, I encountered an error. Please try again.',
      };
      updateSession(activeSessionId, [...updatedMessages, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  return {
    sessions,
    activeSessionId,
    activeSession: sessions.find(s => s.id === activeSessionId),
    isLoading,
    createNewSession,
    setActiveSession,
    sendMessage,
  };
};
