
import React, { useState } from 'react';
import { ChatHistory } from './components/ChatHistory';
import { ChatArea } from './components/ChatArea';
import { useChatManager } from './hooks/useChatManager';
import { MenuIcon, XIcon } from './components/Icons';

const App: React.FC = () => {
  const chatManager = useChatManager();
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);

  return (
    <div className="flex h-screen w-full text-gray-200 bg-brand-bg font-sans">
      <div
        className={`fixed inset-y-0 left-0 z-30 transform ${
          isSidebarOpen ? 'translate-x-0' : '-translate-x-full'
        } transition-transform duration-300 ease-in-out md:relative md:translate-x-0 md:flex md:flex-shrink-0`}
      >
        <ChatHistory
          sessions={chatManager.sessions}
          activeSessionId={chatManager.activeSessionId}
          onNewSession={chatManager.createNewSession}
          onSelectSession={chatManager.setActiveSession}
        />
      </div>
      
      <div className="fixed top-4 left-4 z-40 md:hidden">
        <button onClick={() => setIsSidebarOpen(!isSidebarOpen)} className="p-2 rounded-md bg-sidebar-bg/80 backdrop-blur-sm">
          {isSidebarOpen ? <XIcon className="h-6 w-6" /> : <MenuIcon className="h-6 w-6" />}
        </button>
      </div>

      <main className="flex-1 flex flex-col h-screen overflow-hidden">
        <ChatArea
          session={chatManager.activeSession}
          isLoading={chatManager.isLoading}
          onSendMessage={chatManager.sendMessage}
        />
      </main>
    </div>
  );
};

export default App;
