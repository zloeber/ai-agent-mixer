import React, { useEffect, useState, useCallback } from 'react';
import AgentConfigPanel, { AgentConfigData } from './components/AgentConfigPanel';
import ConversationExchange from './components/ConversationExchange';
import ConfigurationPanel from './components/ConfigurationPanel';
import ControlPanel from './components/ControlPanel';
import websocketService from './services/websocketService';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const App: React.FC = () => {
  const [isConnected, setIsConnected] = useState(false);
  const [agentConfigChanges, setAgentConfigChanges] = useState<Record<string, AgentConfigData>>({});
  const [agentIds, setAgentIds] = useState<string[]>(['agent_a', 'agent_b']);
  const [agentNames, setAgentNames] = useState<Record<string, string>>({
    agent_a: 'Agent A',
    agent_b: 'Agent B'
  });
  const [configVersion, setConfigVersion] = useState(0);

  // Load agent IDs and names from config
  const loadAgentInfo = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/config/export`);
      if (response.ok) {
        const config = await response.json();
        if (config.agents) {
          const ids = Object.keys(config.agents);
          const names: Record<string, string> = {};
          ids.forEach(id => {
            names[id] = config.agents[id].name;
          });
          setAgentIds(ids);
          setAgentNames(names);
          setConfigVersion(prev => prev + 1);
        }
      }
    } catch (error) {
      console.error('Error loading agent info:', error);
    }
  }, []);

  // Check config on mount
  useEffect(() => {
    const checkConfig = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/health`);
        if (response.ok) {
          const data = await response.json();
          if (data.config_loaded) {
            await loadAgentInfo();
          }
        }
      } catch (error) {
        console.error('Error checking config:', error);
      }
    };

    checkConfig();
  }, [loadAgentInfo]);

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

  const handleConfigApplied = async () => {
    // Reload agent info when config is applied
    await loadAgentInfo();
    // Clear any pending changes
    setAgentConfigChanges({});
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
      <ControlPanel onScenarioChange={loadAgentInfo} />

      {/* Main content - Three column layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Dynamically render agent panels based on loaded config */}
        {agentIds.length >= 1 && (
          <div className="w-1/4 min-w-[300px] max-w-[400px] hidden lg:block">
            <AgentConfigPanel 
              key={`${agentIds[0]}-${configVersion}`}
              agentId={agentIds[0]} 
              agentName={agentNames[agentIds[0]]}
              onConfigChange={handleAgentConfigChange}
              configVersion={configVersion}
            />
          </div>
        )}

        {/* Center column - Conversation Exchange */}
        <div className="flex-1 min-w-0">
          <ConversationExchange />
        </div>

        {/* Second agent panel */}
        {agentIds.length >= 2 && (
          <div className="w-1/4 min-w-[300px] max-w-[400px] hidden lg:block">
            <AgentConfigPanel 
              key={`${agentIds[1]}-${configVersion}`}
              agentId={agentIds[1]} 
              agentName={agentNames[agentIds[1]]}
              onConfigChange={handleAgentConfigChange}
              configVersion={configVersion}
            />
          </div>
        )}
      </div>

      {/* Bottom panel - Configuration */}
      <ConfigurationPanel 
        agentConfigChanges={agentConfigChanges}
        onConfigApplied={handleConfigApplied}
      />
    </div>
  );
};

export default App;
