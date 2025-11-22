import React, { useEffect, useState } from 'react';
import AgentConfigPanel, { AgentConfigData } from './components/AgentConfigPanel';
import ConversationExchange from './components/ConversationExchange';
import ConfigurationPanel from './components/ConfigurationPanel';
import ControlPanel from './components/ControlPanel';
import websocketService from './services/websocketService';

const App: React.FC = () => {
  const [isConnected, setIsConnected] = useState(false);
  const [agentConfigChanges, setAgentConfigChanges] = useState<Record<string, AgentConfigData>>({});

  useEffect(() => {
    // Connect to WebSocket
    websocketService.connect();

    // Subscribe to connection events
    const unsubscribe = websocketService.subscribe('connection', (data: any) => {
      setIsConnected(data.status === 'connected');
    });

    return () => {
      unsubscribe();
      websocketService.disconnect();
    };
  }, []);

  const handleAgentConfigChange = (agentId: string, config: AgentConfigData) => {
    setAgentConfigChanges(prev => ({
      ...prev,
      [agentId]: config
    }));
  };

  return (
    <div className="flex flex-col h-screen bg-gray-900">
      {/* Header */}
      <header className="bg-gray-950 border-b border-gray-700 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <h1 className="text-2xl font-bold text-white">
              🤖 AI Agent Mixer
            </h1>
            <span className={`px-2 py-1 text-xs rounded ${
              isConnected ? 'bg-green-600 text-white' : 'bg-red-600 text-white'
            }`}>
              {isConnected ? '● Connected' : '○ Disconnected'}
            </span>
          </div>
        </div>
      </header>

      {/* Control Panel */}
      <ControlPanel />

      {/* Main content - Three column layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left column - Agent A Config Panel */}
        <div className="w-1/4 min-w-[300px] max-w-[400px] hidden lg:block">
          <AgentConfigPanel 
            agentId="agent_a" 
            agentName="Agent A"
            onConfigChange={handleAgentConfigChange}
          />
        </div>

        {/* Center column - Conversation Exchange */}
        <div className="flex-1 min-w-0">
          <ConversationExchange />
        </div>

        {/* Right column - Agent B Config Panel */}
        <div className="w-1/4 min-w-[300px] max-w-[400px] hidden lg:block">
          <AgentConfigPanel 
            agentId="agent_b" 
            agentName="Agent B"
            onConfigChange={handleAgentConfigChange}
          />
        </div>
      </div>

      {/* Bottom panel - Configuration */}
      <ConfigurationPanel agentConfigChanges={agentConfigChanges} />
    </div>
  );
};

export default App;
