import React, { useState } from 'react';

interface AgentConsoleProps {
  agentId: string;
  agentName?: string;
}

const AgentConsole: React.FC<AgentConsoleProps> = ({ agentId, agentName }) => {
  const [messages, setMessages] = useState<string[]>([]);

  const clearConsole = () => {
    setMessages([]);
  };

  return (
    <div className="flex flex-col h-full bg-gray-900 border-r border-gray-700">
      {/* Header */}
      <div className="p-4 border-b border-gray-700 bg-gray-800">
        <div className="flex justify-between items-center">
          <h2 className="text-lg font-semibold text-white">
            {agentName || agentId} Console
          </h2>
          <button
            onClick={clearConsole}
            className="px-3 py-1 text-xs bg-gray-700 hover:bg-gray-600 text-white rounded transition-colors"
          >
            Clear
          </button>
        </div>
      </div>

      {/* Console content */}
      <div className="flex-1 overflow-y-auto p-4 font-mono text-sm">
        {messages.length === 0 ? (
          <div className="text-gray-500 italic">
            Waiting for agent thoughts...
          </div>
        ) : (
          messages.map((msg, idx) => (
            <div key={idx} className="text-green-400 mb-1">
              {msg}
            </div>
          ))
        )}
      </div>

      {/* Status bar */}
      <div className="p-2 border-t border-gray-700 bg-gray-800">
        <div className="text-xs text-gray-400">
          Messages: {messages.length}
        </div>
      </div>
    </div>
  );
};

export default AgentConsole;
