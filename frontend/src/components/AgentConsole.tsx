import React, { useState, useEffect, useRef } from 'react';
import websocketService from '../services/websocketService';

interface AgentConsoleProps {
  agentId: string;
  agentName?: string;
}

interface ThoughtMessage {
  type: 'thought';
  content: string;
  timestamp: string;
}

const AgentConsole: React.FC<AgentConsoleProps> = ({ agentId, agentName }) => {
  const [messages, setMessages] = useState<ThoughtMessage[]>([]);
  const consoleEndRef = useRef<HTMLDivElement>(null);
  const consoleContainerRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState(true);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (autoScroll && consoleEndRef.current) {
      consoleEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, autoScroll]);

  // Subscribe to WebSocket events for this agent
  useEffect(() => {
    const unsubscribe = websocketService.subscribe('thought', (data: any) => {
      // Only handle thoughts for this agent
      if (data.agent_id === agentId) {
        setMessages(prev => [...prev, {
          type: 'thought',
          content: data.content,
          timestamp: data.timestamp
        }]);
      }
    });

    return () => {
      unsubscribe();
    };
  }, [agentId]);

  // Handle scroll to detect if user manually scrolled up
  const handleScroll = () => {
    if (consoleContainerRef.current) {
      const { scrollTop, scrollHeight, clientHeight } = consoleContainerRef.current;
      const isAtBottom = scrollHeight - scrollTop - clientHeight < 50;
      setAutoScroll(isAtBottom);
    }
  };

  const clearConsole = () => {
    setMessages([]);
  };

  const formatTimestamp = (timestamp: string) => {
    try {
      const date = new Date(timestamp);
      return date.toLocaleTimeString();
    } catch {
      return timestamp;
    }
  };

  return (
    <div className="flex flex-col h-full bg-gray-900">
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
      <div 
        ref={consoleContainerRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto p-4 font-mono text-sm"
      >
        {messages.length === 0 ? (
          <div className="text-gray-500 italic">
            Waiting for agent thoughts...
          </div>
        ) : (
          <>
            {messages.map((msg, idx) => (
              <div key={idx} className="mb-2">
                <span className="text-gray-500 text-xs mr-2">
                  {formatTimestamp(msg.timestamp)}
                </span>
                <span className="text-green-400">
                  {msg.content}
                </span>
              </div>
            ))}
            <div ref={consoleEndRef} />
          </>
        )}
      </div>

      {/* Status bar */}
      <div className="p-2 border-t border-gray-700 bg-gray-800">
        <div className="flex justify-between items-center text-xs text-gray-400">
          <span>Messages: {messages.length}</span>
          {!autoScroll && (
            <button
              onClick={() => {
                setAutoScroll(true);
                consoleEndRef.current?.scrollIntoView({ behavior: 'smooth' });
              }}
              className="text-blue-400 hover:text-blue-300"
            >
              ↓ Jump to bottom
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default AgentConsole;
