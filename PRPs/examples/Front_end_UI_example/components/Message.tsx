
import React from 'react';
import type { ChatMessage, FileAttachment } from '../types';
import { PaperclipIcon, DocumentIcon } from './Icons';

const isImage = (file: FileAttachment) => file.type.startsWith('image/');

const FilePreview: React.FC<{ file: FileAttachment }> = ({ file }) => {
  if (isImage(file)) {
    return (
      <img
        src={file.content}
        alt={file.name}
        className="max-w-xs max-h-48 rounded-lg object-contain"
      />
    );
  }
  return (
    <div className="flex items-center gap-2 p-2 rounded-lg bg-gray-600/50 text-sm">
      <DocumentIcon className="h-5 w-5 flex-shrink-0" />
      <span className="truncate">{file.name}</span>
    </div>
  );
};

export const Message: React.FC<{ message: ChatMessage }> = ({ message }) => {
  const isUser = message.role === 'user';

  return (
    <div className={`flex items-start gap-4 ${isUser ? 'justify-end' : ''}`}>
      {!isUser && (
         <div className="w-10 h-10 rounded-full bg-gray-700 flex-shrink-0 flex items-center justify-center font-bold">G</div>
      )}
      <div
        className={`flex flex-col gap-2 max-w-xl ${isUser ? 'items-end' : 'items-start'}`}
      >
        <div className={`p-4 rounded-2xl ${isUser ? 'bg-accent/80 text-white rounded-br-none' : 'bg-message-user rounded-bl-none'}`}>
          <p className="whitespace-pre-wrap">{message.text}</p>
        </div>
        {message.files && message.files.length > 0 && (
          <div className="flex flex-wrap gap-2 mt-2">
            {message.files.map((file, index) => (
              <FilePreview key={index} file={file} />
            ))}
          </div>
        )}
      </div>
      {isUser && (
         <div className="w-10 h-10 rounded-full bg-gray-600 flex-shrink-0 flex items-center justify-center font-bold">U</div>
      )}
    </div>
  );
};
