
import React from 'react';
import type { ChatSession } from '../types';
import { ChatWindow } from './ChatWindow';
import { MessageInput } from './MessageInput';

interface ChatAreaProps {
  session: ChatSession | undefined;
  isLoading: boolean;
  onSendMessage: (text: string, files: File[]) => Promise<void>;
}

export const ChatArea: React.FC<ChatAreaProps> = ({ session, isLoading, onSendMessage }) => {
  if (!session) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center text-gray-400">
        <h1 className="text-2xl font-semibold">Chat</h1>
        <p>Start a new conversation to begin.</p>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col h-full">
      <ChatWindow messages={session.messages} isLoading={isLoading} />
      <div className="w-full max-w-4xl mx-auto px-4">
        <MessageInput onSendMessage={onSendMessage} isLoading={isLoading} />
      </div>
    </div>
  );
};
