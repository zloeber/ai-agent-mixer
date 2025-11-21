import React, { useState, useEffect, useRef } from 'react';
import websocketService from '../services/websocketService';

interface Message {
  id: string;
  agent_id: string;
  agent_name: string;
  content: string;
  timestamp: string;
  cycle?: number;
}

let messageIdCounter = 0;

const ConversationExchange: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [currentCycle, setCurrentCycle] = useState(0);
  const [currentTurnAgent, setCurrentTurnAgent] = useState<string | null>(null);
  const [isPaused, setIsPaused] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Subscribe to WebSocket events
  useEffect(() => {
    const unsubscribeMessage = websocketService.subscribe('conversation_message', (data: any) => {
      const message: Message = {
        id: `msg-${++messageIdCounter}-${Date.now()}`,
        agent_id: data.agent_id,
        agent_name: data.agent_name,
        content: data.content,
        timestamp: data.timestamp,
        cycle: data.cycle
      };
      setMessages(prev => [...prev, message]);
      if (data.cycle !== undefined) {
        setCurrentCycle(data.cycle);
      }
    });

    const unsubscribeTurn = websocketService.subscribe('turn_indicator', (data: any) => {
      setCurrentTurnAgent(data.agent_id);
    });

    const unsubscribeStatus = websocketService.subscribe('conversation_status', (data: any) => {
      if (data.status === 'paused') {
        setIsPaused(true);
      } else if (data.status === 'resumed') {
        setIsPaused(false);
      }
    });

    const unsubscribeStarted = websocketService.subscribe('conversation_started', (data: any) => {
      setMessages([]);
      setCurrentCycle(0);
      setCurrentTurnAgent(data.starting_agent);
      setIsPaused(false);
    });

    const unsubscribeEnded = websocketService.subscribe('conversation_ended', () => {
      setCurrentTurnAgent(null);
    });

    return () => {
      unsubscribeMessage();
      unsubscribeTurn();
      unsubscribeStatus();
      unsubscribeStarted();
      unsubscribeEnded();
    };
  }, []);

  const exportConversation = () => {
    // Create markdown format
    let markdown = `# Conversation Export\n\n`;
    markdown += `**Date:** ${new Date().toISOString()}\n`;
    markdown += `**Total Messages:** ${messages.length}\n`;
    markdown += `**Cycles Completed:** ${currentCycle}\n\n`;
    markdown += `---\n\n`;

    messages.forEach((msg) => {
      markdown += `### ${msg.agent_name} (${msg.agent_id}) - ${msg.timestamp}\n`;
      if (msg.cycle !== undefined) {
        markdown += `*Cycle ${msg.cycle}*\n\n`;
      }
      markdown += `${msg.content}\n\n`;
      markdown += `---\n\n`;
    });

    // Create and download file
    const blob = new Blob([markdown], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `conversation-${Date.now()}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const togglePause = async () => {
    try {
      const endpoint = isPaused ? '/api/conversation/resume' : '/api/conversation/pause';
      const response = await fetch(`http://localhost:8000${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      
      if (!response.ok) {
        console.error('Failed to toggle pause');
      }
      // Status will be updated via WebSocket event
    } catch (error) {
      console.error('Error toggling pause:', error);
    }
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
            {currentTurnAgent && (
              <div className="text-sm text-yellow-400">
                🔄 {currentTurnAgent}'s turn
              </div>
            )}
            <button
              onClick={togglePause}
              className="px-3 py-1 text-xs bg-yellow-600 hover:bg-yellow-700 text-white rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              disabled={messages.length === 0}
            >
              {isPaused ? '▶️ Resume' : '⏸️ Pause'}
            </button>
            <button
              onClick={exportConversation}
              className="px-3 py-1 text-xs bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              disabled={messages.length === 0}
            >
              📥 Export
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
          <>
            {messages.map((msg) => {
              const isCurrentTurn = currentTurnAgent === msg.agent_id;
              return (
                <div
                  key={msg.id}
                  className={`flex ${
                    msg.agent_id === 'agent_a' ? 'justify-start' : 'justify-end'
                  }`}
                >
                  <div
                    className={`max-w-[70%] rounded-lg p-4 ${
                      msg.agent_id === 'agent_a'
                        ? 'bg-blue-600 text-white'
                        : 'bg-green-600 text-white'
                    } ${isCurrentTurn ? 'ring-2 ring-yellow-400' : ''}`}
                  >
                    <div className="flex items-center space-x-2 mb-2">
                      <span className="font-semibold text-sm">{msg.agent_name}</span>
                      <span className="text-xs opacity-75">{formatTimestamp(msg.timestamp)}</span>
                      {msg.cycle !== undefined && (
                        <span className="text-xs opacity-75">Cycle {msg.cycle}</span>
                      )}
                    </div>
                    <div className="text-sm whitespace-pre-wrap">{msg.content}</div>
                  </div>
                </div>
              );
            })}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>
    </div>
  );
};

export default ConversationExchange;
