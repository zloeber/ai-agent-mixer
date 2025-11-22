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
  const [isRunning, setIsRunning] = useState(false);
  const [isTerminated, setIsTerminated] = useState(false);
  const [conversationStarted, setConversationStarted] = useState(false);
  const [maxCycles, setMaxCycles] = useState(0);
  const [shouldAutoRun, setShouldAutoRun] = useState(false);
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

    const unsubscribeStarted = websocketService.subscribe('conversation_started', (data: any) => {
      setMessages([]);
      setCurrentCycle(0);
      setCurrentTurnAgent(data.starting_agent);
      setIsRunning(true);
      setIsTerminated(false);
      setConversationStarted(true);
      setMaxCycles(data.max_cycles || 0);
      
      // Trigger auto-run
      setShouldAutoRun(true);
    });

    const unsubscribeEnded = websocketService.subscribe('conversation_ended', () => {
      setCurrentTurnAgent(null);
      setIsRunning(false);
      setIsTerminated(true);
    });

    const unsubscribeError = websocketService.subscribe('conversation_error', () => {
      setCurrentTurnAgent(null);
      setIsRunning(false);
      setIsTerminated(true);
    });

    return () => {
      unsubscribeMessage();
      unsubscribeTurn();
      unsubscribeStarted();
      unsubscribeEnded();
      unsubscribeError();
    };
  }, []);

  // Auto-run conversation after it starts
  useEffect(() => {
    if (shouldAutoRun) {
      setShouldAutoRun(false);
      // Small delay to ensure state is settled
      const timer = setTimeout(async () => {
        try {
          setIsRunning(true);
          const response = await fetch('http://localhost:8000/api/conversation/continue?cycles=1', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
          });
          
          if (!response.ok) {
            const error = await response.json();
            console.error('Failed to auto-continue conversation:', error);
            setIsRunning(false);
          } else {
            const result = await response.json();
            console.log('Auto-continued conversation:', result);
            
            if (result.terminated) {
              setIsRunning(false);
              setIsTerminated(true);
              setCurrentTurnAgent(null);
            } else {
              setIsRunning(false);
            }
          }
        } catch (error) {
          console.error('Error auto-continuing conversation:', error);
          setIsRunning(false);
        }
      }, 200);
      
      return () => clearTimeout(timer);
    }
  }, [shouldAutoRun]);

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

  const runCycles = async (cycles: number) => {
    try {
      setIsRunning(true);
      const response = await fetch(`http://localhost:8000/api/conversation/continue?cycles=${cycles}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      
      if (!response.ok) {
        const error = await response.json();
        console.error('Failed to continue conversation:', error);
        alert(`Failed to continue: ${error.detail}`);
        setIsRunning(false);
      } else {
        const result = await response.json();
        console.log('Continued conversation:', result);
        
        // Update state based on response
        if (result.terminated) {
          setIsRunning(false);
          setIsTerminated(true);
          setCurrentTurnAgent(null);
        } else {
          setIsRunning(false);
        }
      }
    } catch (error) {
      console.error('Error continuing conversation:', error);
      alert('Failed to continue conversation');
      setIsRunning(false);
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
              {maxCycles > 0 && <span className="text-gray-500"> / {maxCycles}</span>}
            </div>
            {currentTurnAgent && (
              <div className="text-sm text-yellow-400">
                🔄 {currentTurnAgent}'s turn
              </div>
            )}
            
            {/* Cycle Control Buttons - show when conversation started and not terminated */}
            {conversationStarted && !isTerminated && (
              <div className="flex items-center space-x-2 border-l border-gray-600 pl-4">
                <span className="text-xs text-gray-400">Run:</span>
                <button
                  onClick={() => runCycles(1)}
                  disabled={isRunning}
                  className="px-3 py-1 text-xs bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  title="Run 1 cycle"
                >
                  +1
                </button>
                <button
                  onClick={() => runCycles(5)}
                  disabled={isRunning}
                  className="px-3 py-1 text-xs bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  title="Run 5 cycles"
                >
                  +5
                </button>
                <button
                  onClick={() => runCycles(10)}
                  disabled={isRunning}
                  className="px-3 py-1 text-xs bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  title="Run 10 cycles"
                >
                  +10
                </button>
                <button
                  onClick={() => runCycles(maxCycles - currentCycle)}
                  disabled={isRunning || maxCycles <= currentCycle}
                  className="px-3 py-1 text-xs bg-purple-600 hover:bg-purple-700 text-white rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  title="Run to completion"
                >
                  ▶️ All
                </button>
                {isRunning && (
                  <span className="text-xs text-yellow-400 animate-pulse">Running...</span>
                )}
              </div>
            )}
            
            {/* Show terminated status */}
            {isTerminated && (
              <div className="text-sm text-green-400 border-l border-gray-600 pl-4">
                ✓ Conversation Complete
              </div>
            )}
            
            <button
              onClick={exportConversation}
              className="px-3 py-1 text-xs bg-green-600 hover:bg-green-700 text-white rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
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
              // Determine if this is the left agent (first agent that appears)
              const firstAgentId = messages[0]?.agent_id;
              const isLeftAgent = msg.agent_id === firstAgentId;
              
              // Assign darker, distinct colors for each agent
              const agentColor = isLeftAgent
                ? 'bg-slate-700 text-gray-100'
                : 'bg-indigo-900 text-gray-100';
              
              return (
                <div
                  key={msg.id}
                  className={`flex ${isLeftAgent ? 'justify-start' : 'justify-end'}`}
                >
                  <div
                    className={`max-w-[70%] rounded-lg p-4 ${agentColor} ${
                      isCurrentTurn ? 'ring-2 ring-yellow-400' : ''
                    }`}
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
