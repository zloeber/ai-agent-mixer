import React, { useState } from 'react';

interface Message {
  id: string;
  agentId: string;
  agentName: string;
  content: string;
  timestamp: string;
  cycle?: number;
}

const ConversationExchange: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [currentCycle, setCurrentCycle] = useState(0);

  return (
    <div className="flex flex-col h-full bg-gray-800">
      {/* Header */}
      <div className="p-4 border-b border-gray-700 bg-gray-900">
        <div className="flex justify-between items-center">
          <h2 className="text-lg font-semibold text-white">
            Conversation Exchange
          </h2>
          <div className="flex items-center space-x-4">
            <div className="text-sm text-gray-400">
              Cycle: <span className="text-white font-semibold">{currentCycle}</span>
            </div>
            <button className="px-3 py-1 text-xs bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors">
              Export
            </button>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-gray-500 text-center">
              <div className="text-4xl mb-2">💬</div>
              <div>No conversation yet</div>
              <div className="text-sm mt-1">Configure and start agents to begin</div>
            </div>
          </div>
        ) : (
          messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex ${
                msg.agentId === 'agent_a' ? 'justify-start' : 'justify-end'
              }`}
            >
              <div
                className={`max-w-[70%] rounded-lg p-4 ${
                  msg.agentId === 'agent_a'
                    ? 'bg-blue-600 text-white'
                    : 'bg-green-600 text-white'
                }`}
              >
                <div className="flex items-center space-x-2 mb-2">
                  <span className="font-semibold text-sm">{msg.agentName}</span>
                  <span className="text-xs opacity-75">{msg.timestamp}</span>
                  {msg.cycle && (
                    <span className="text-xs opacity-75">Cycle {msg.cycle}</span>
                  )}
                </div>
                <div className="text-sm whitespace-pre-wrap">{msg.content}</div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default ConversationExchange;
