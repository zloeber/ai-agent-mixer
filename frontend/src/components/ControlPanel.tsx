import React, { useState, useEffect } from 'react';
import websocketService from '../services/websocketService';

interface ControlPanelProps {
  onConversationStart?: () => void;
  onScenarioChange?: () => void;
}

type ConversationStatus = 'idle' | 'starting' | 'running' | 'paused' | 'stopping' | 'terminated';

interface Scenario {
  name: string;
  goal: string;
  brevity: string;
  max_cycles: number;
  starting_agent: string;
  agents_involved?: string[];
}

interface AgentConfigData {
  name: string;
  persona: string;
  model: {
    provider: string;
    url: string;
    model_name: string;
    thinking: boolean;
    parameters: {
      temperature: number;
      top_p: number;
      [key: string]: string | number | boolean;
    };
  };
  mcp_servers: string[];
  metadata: {
    [key: string]: unknown;
  };
}

const ControlPanel: React.FC<ControlPanelProps> = ({ onConversationStart, onScenarioChange }) => {
  const [status, setStatus] = useState<ConversationStatus>('idle');
  const [currentCycle, setCurrentCycle] = useState(0);
  const [maxCycles, setMaxCycles] = useState(5);
  const [messageCount, setMessageCount] = useState(0);
  const [startingAgent, setStartingAgent] = useState<string>('');
  const [configLoaded, setConfigLoaded] = useState(false);
  const [allAgents, setAllAgents] = useState<string[]>([]);
  const [availableAgents, setAvailableAgents] = useState<string[]>([]);
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [selectedScenario, setSelectedScenario] = useState<string | null>(null);
  const [, setIsTerminated] = useState(false);
  const [conversationStarted, setConversationStarted] = useState(false);

  // Check if configuration is loaded and fetch scenarios
  useEffect(() => {
    const checkConfig = async () => {
      try {
        const response = await fetch('http://localhost:8000/health');
        if (response.ok) {
          const data = await response.json();
          setConfigLoaded(data.config_loaded);
          
          // Fetch scenarios and agent list if config is loaded
          if (data.config_loaded) {
            try {
              // Fetch scenarios
              const scenariosResponse = await fetch('http://localhost:8000/api/conversation/scenarios');
              let scenariosData: { scenarios: Scenario[], default: string | null } | null = null;
              if (scenariosResponse.ok) {
                scenariosData = await scenariosResponse.json();
                if (scenariosData) {
                  setScenarios(scenariosData.scenarios);
                  // Set default scenario if none selected
                  if (!selectedScenario && scenariosData.default) {
                    setSelectedScenario(scenariosData.default);
                  }
                }
              }

              // Fetch agent list from config
              const configResponse = await fetch('http://localhost:8000/api/config/export');
              if (configResponse.ok) {
                const config: { agents: Record<string, AgentConfigData> } = await configResponse.json();
                if (config.agents) {
                  const agentIds = Object.keys(config.agents);
                  setAllAgents(agentIds);
                  
                  // Set available agents based on first scenario or all agents
                  if (scenariosData && scenariosData.scenarios && scenariosData.scenarios.length > 0) {
                    const firstScenario = scenariosData.scenarios[0];
                    if (firstScenario.agents_involved && firstScenario.agents_involved.length > 0) {
                      setAvailableAgents(firstScenario.agents_involved);
                    } else {
                      setAvailableAgents(agentIds);
                    }
                    setStartingAgent(firstScenario.starting_agent);
                  } else {
                    setAvailableAgents(agentIds);
                    if (agentIds.length > 0) {
                      setStartingAgent(agentIds[0]);
                    }
                  }
                }
              }
            } catch (error) {
              console.error('Error fetching scenarios or agents:', error);
            }
          }
        }
      } catch (error) {
        console.error('Error checking config:', error);
      }
    };

    checkConfig();
    const interval = setInterval(checkConfig, 3000); // Check every 3 seconds

    return () => clearInterval(interval);
  }, [selectedScenario]);

  // Subscribe to WebSocket events
  useEffect(() => {
    const unsubscribeStarted = websocketService.subscribe('conversation_started', (data: any) => {
      setStatus('running');
      setCurrentCycle(0);
      setMessageCount(0);
      setIsTerminated(false);
      setConversationStarted(true);
      if (data.max_cycles) {
        setMaxCycles(data.max_cycles);
      }
      if (data.agents) {
        setAvailableAgents(data.agents);
      }
      if (onConversationStart) {
        onConversationStart();
      }
    });

    const unsubscribeMessage = websocketService.subscribe('conversation_message', (data: any) => {
      if (data.cycle !== undefined) {
        setCurrentCycle(data.cycle);
      }
      setMessageCount(prev => prev + 1);
    });

    const unsubscribeEnded = websocketService.subscribe('conversation_ended', () => {
      setStatus('terminated');
      setIsTerminated(true);
    });

    const unsubscribeStatus = websocketService.subscribe('conversation_status', (data: any) => {
      if (data.status === 'paused') {
        setStatus('paused');
      } else if (data.status === 'resumed') {
        setStatus('running');
      }
    });

    const unsubscribeError = websocketService.subscribe('conversation_error', (data: any) => {
      setStatus('terminated');
      setIsTerminated(true);
      console.error('Conversation error:', data.error);
    });

    return () => {
      unsubscribeStarted();
      unsubscribeMessage();
      unsubscribeEnded();
      unsubscribeStatus();
      unsubscribeError();
    };
  }, [onConversationStart]);

  const handleStartConversation = async () => {
    if (!configLoaded) {
      alert('Please load a configuration first');
      return;
    }

    setStatus('starting');

    try {
      // Build URL with optional scenario parameter and overrides
      const url = new URL('http://localhost:8000/api/conversation/start');
      if (selectedScenario) {
        url.searchParams.append('scenario', selectedScenario);
      }
      // Add runtime overrides
      if (maxCycles) {
        url.searchParams.append('max_cycles', maxCycles.toString());
      }
      if (startingAgent) {
        url.searchParams.append('starting_agent', startingAgent);
      }
      
      const response = await fetch(url.toString(), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });

      if (response.ok) {
        const data = await response.json();
        console.log('Conversation started:', data);
      } else {
        const errorData = await response.json();
        alert(`Failed to start conversation: ${errorData.detail}`);
        setStatus('idle');
      }
    } catch (error) {
      console.error('Error starting conversation:', error);
      alert('Failed to start conversation');
      setStatus('idle');
    }
  };

  const handleStopConversation = async () => {
    setStatus('stopping');

    try {
      const response = await fetch('http://localhost:8000/api/conversation/stop', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });

      if (response.ok) {
        setStatus('idle');
        setCurrentCycle(0);
        setMessageCount(0);
      }
    } catch (error) {
      console.error('Error stopping conversation:', error);
    }
  };

  const handleClearConversation = () => {
    // Reset all conversation state
    setStatus('idle');
    setCurrentCycle(0);
    setMessageCount(0);
    setIsTerminated(false);
    setConversationStarted(false);
    
    // Broadcast clear event to other components
    websocketService.subscribe('clear', () => {});
    
    // Trigger a synthetic event for components to clear their state
    // We'll use a custom event
    window.dispatchEvent(new CustomEvent('clearConversation'));
  };

  const getStatusColor = () => {
    switch (status) {
      case 'idle':
        return 'bg-gray-600';
      case 'starting':
        return 'bg-yellow-600 animate-pulse';
      case 'running':
        return 'bg-green-600 animate-pulse';
      case 'paused':
        return 'bg-yellow-600';
      case 'stopping':
        return 'bg-orange-600 animate-pulse';
      case 'terminated':
        return 'bg-red-600';
      default:
        return 'bg-gray-600';
    }
  };

  const getStatusText = () => {
    switch (status) {
      case 'idle':
        return 'Ready';
      case 'starting':
        return 'Starting...';
      case 'running':
        return 'Running';
      case 'paused':
        return 'Paused';
      case 'stopping':
        return 'Stopping...';
      case 'terminated':
        return 'Completed';
      default:
        return 'Unknown';
    }
  };

  const canStart = configLoaded && (status === 'idle' || status === 'terminated');
  const canStop = status === 'running' || status === 'paused';

  return (
    <div className="bg-gray-950 border-b border-gray-700 p-4">
      <div className="flex items-center justify-between">
        {/* Left: Status and Progress */}
        <div className="flex items-center space-x-6">
          <div className="flex items-center space-x-3">
            <div className={`w-3 h-3 rounded-full ${getStatusColor()}`} />
            <span className="text-white font-semibold">{getStatusText()}</span>
          </div>

          {status !== 'idle' && (
            <>
              <div className="text-sm text-gray-400">
                Cycle: <span className="text-white font-semibold">{currentCycle}</span>
                <span className="text-gray-500"> / {maxCycles}</span>
              </div>

              <div className="text-sm text-gray-400">
                Messages: <span className="text-white font-semibold">{messageCount}</span>
              </div>

              {/* Progress Bar */}
              <div className="w-48 bg-gray-700 rounded-full h-2">
                <div
                  className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${Math.min((currentCycle / maxCycles) * 100, 100)}%` }}
                />
              </div>
            </>
          )}
        </div>

        {/* Right: Controls */}
        <div className="flex items-center space-x-4">
          {/* Configuration Overrides */}
          {status === 'idle' && (
            <>
              {/* Scenario Selector */}
              {scenarios.length > 0 && (
                <div className="flex items-center space-x-2">
                  <label className="text-sm text-gray-400">Scenario:</label>
                  <select
                    value={selectedScenario || ''}
                    onChange={(e) => {
                      const newScenario = e.target.value || null;
                      setSelectedScenario(newScenario);
                      
                      // Update starting agent, max cycles, and available agents from selected scenario
                      if (newScenario) {
                        const scenario = scenarios.find(s => s.name === newScenario);
                        if (scenario) {
                          setStartingAgent(scenario.starting_agent);
                          setMaxCycles(scenario.max_cycles);
                          
                          // Update available agents based on scenario's agents_involved
                          if (scenario.agents_involved && scenario.agents_involved.length > 0) {
                            setAvailableAgents(scenario.agents_involved);
                          } else {
                            // If no agents_involved specified, use all agents
                            setAvailableAgents(allAgents);
                          }
                        }
                      }
                      
                      // Notify parent to reload agent configs
                      if (onScenarioChange) {
                        onScenarioChange();
                      }
                    }}
                    className="px-3 py-1 text-sm bg-gray-800 text-white rounded border border-gray-700 focus:outline-none focus:border-blue-500"
                    disabled={!configLoaded}
                  >
                    {scenarios.map(scenario => (
                      <option key={scenario.name} value={scenario.name}>
                        {scenario.name}
                      </option>
                    ))}
                  </select>
                </div>
              )}
              
              <div className="flex items-center space-x-2">
                <label className="text-sm text-gray-400">Starting Agent:</label>
                <select
                  value={startingAgent}
                  onChange={(e) => setStartingAgent(e.target.value)}
                  className="px-2 py-1 text-sm bg-gray-800 text-white rounded border border-gray-700 focus:outline-none focus:border-blue-500"
                  disabled={!configLoaded}
                >
                  {availableAgents.map(agent => (
                    <option key={agent} value={agent}>{agent}</option>
                  ))}
                </select>
              </div>

              <div className="flex items-center space-x-2">
                <label className="text-sm text-gray-400">Max Cycles:</label>
                <input
                  type="number"
                  value={maxCycles}
                  onChange={(e) => setMaxCycles(Math.max(1, parseInt(e.target.value) || 1))}
                  min="1"
                  max="100"
                  className="w-20 px-2 py-1 text-sm bg-gray-800 text-white rounded border border-gray-700 focus:outline-none focus:border-blue-500"
                  disabled={!configLoaded}
                />
              </div>
            </>
          )}

          {/* Action Buttons */}
          <button
            onClick={handleStartConversation}
            disabled={!canStart}
            className="px-6 py-2 bg-green-600 hover:bg-green-700 text-white rounded font-semibold transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            ▶️ Start
          </button>

          <button
            onClick={handleStopConversation}
            disabled={!canStop}
            className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            ⏹️ Stop
          </button>

          <button
            onClick={handleClearConversation}
            disabled={!conversationStarted}
            className="px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            title="Clear conversation and reset interface"
          >
            🧹 Clear
          </button>
        </div>
      </div>
    </div>
  );
};

export default ControlPanel;
