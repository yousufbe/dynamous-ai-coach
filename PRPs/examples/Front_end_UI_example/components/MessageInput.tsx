
import React, { useState, useRef, useCallback } from 'react';
import { PaperclipIcon, SendIcon } from './Icons';

interface MessageInputProps {
  onSendMessage: (text: string, files: File[]) => void;
  isLoading: boolean;
}

const MAX_FILES = 5;

export const MessageInput: React.FC<MessageInputProps> = ({ onSendMessage, isLoading }) => {
  const [text, setText] = useState('');
  const [files, setFiles] = useState<File[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleSendMessage = () => {
    if ((!text.trim() && files.length === 0) || isLoading) return;
    onSendMessage(text, files);
    setText('');
    setFiles([]);
  };
  
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const newFiles = Array.from(e.target.files);
      setFiles(prev => [...prev, ...newFiles].slice(0, MAX_FILES));
    }
  };

  const removeFile = (index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index));
  };

  return (
    <div className="py-4">
        <div className="relative bg-input-bg border border-gray-600 rounded-2xl p-2 flex flex-col">
            {files.length > 0 && (
                <div className="p-2 flex flex-wrap gap-2 border-b border-gray-600 mb-2">
                    {files.map((file, index) => (
                    <div key={index} className="bg-gray-700 rounded-full px-3 py-1 text-sm flex items-center gap-2">
                        <span>{file.name}</span>
                        <button onClick={() => removeFile(index)} className="text-gray-400 hover:text-white">
                        &times;
                        </button>
                    </div>
                    ))}
                </div>
            )}
            <div className="flex items-end">
                <textarea
                    rows={1}
                    value={text}
                    onChange={(e) => setText(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="Type a message or drop a file..."
                    className="flex-1 bg-transparent focus:outline-none resize-none px-2 placeholder-gray-400"
                    style={{ maxHeight: '200px' }}
                />
                <button
                    onClick={() => fileInputRef.current?.click()}
                    className="p-2 text-gray-400 hover:text-accent rounded-full transition-colors"
                    aria-label="Attach file"
                >
                    <PaperclipIcon className="w-6 h-6" />
                </button>
                <input
                    type="file"
                    multiple
                    ref={fileInputRef}
                    onChange={handleFileChange}
                    className="hidden"
                    accept="image/*,application/pdf,text/plain,text/markdown,text/csv"
                />
                <button
                    onClick={handleSendMessage}
                    disabled={isLoading || (!text.trim() && files.length === 0)}
                    className="p-2 text-white bg-accent rounded-full disabled:bg-gray-500 disabled:cursor-not-allowed transition-colors"
                    aria-label="Send message"
                >
                    <SendIcon className="w-6 h-6" />
                </button>
            </div>
        </div>
    </div>
  );
};
