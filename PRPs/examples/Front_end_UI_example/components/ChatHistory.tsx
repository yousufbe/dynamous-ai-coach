
import React from 'react';
import type { ChatSession } from '../types';
import { PlusIcon, ChatBubbleIcon } from './Icons';

interface ChatHistoryProps {
  sessions: ChatSession[];
  activeSessionId: string | null;
  onNewSession: () => void;
  onSelectSession: (id: string) => void;
}

export const ChatHistory: React.FC<ChatHistoryProps> = ({
  sessions,
  activeSessionId,
  onNewSession,
  onSelectSession,
}) => {
  return (
    <aside className="w-64 bg-sidebar-bg flex flex-col h-full p-2">
      <div className="flex-shrink-0 p-2">
        <button
          onClick={onNewSession}
          className="w-full flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium text-gray-200 bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors duration-200"
        >
          <PlusIcon className="w-5 h-5" />
          New Chat
        </button>
      </div>
      <nav className="flex-1 overflow-y-auto mt-4 space-y-1 pr-1">
        {sessions.map((session) => (
          <a
            key={session.id}
            href="#"
            onClick={(e) => {
              e.preventDefault();
              onSelectSession(session.id);
            }}
            className={`flex items-center gap-3 rounded-lg px-3 py-2 transition-all duration-200 ${
              activeSessionId === session.id
                ? 'bg-accent/20 text-accent'
                : 'text-gray-400 hover:bg-gray-700 hover:text-gray-200'
            }`}
          >
            <ChatBubbleIcon className="h-5 w-5 flex-shrink-0" />
            <span className="truncate text-sm font-medium">{session.title}</span>
          </a>
        ))}
      </nav>
      <div className="flex-shrink-0 p-2 mt-auto">
         <p className="text-xs text-gray-500 text-center">Gemini Chat UI</p>
      </div>
    </aside>
  );
};
