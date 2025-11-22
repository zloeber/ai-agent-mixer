import React, { useState, useEffect } from 'react';
import AgentConsole from './AgentConsole';

interface AgentConfigPanelProps {
  agentId: string;
  agentName?: string;
  onConfigChange?: (agentId: string, config: AgentConfigData) => void;
}

export interface AgentConfigData {
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
}

// API configuration
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const AgentConfigPanel: React.FC<AgentConfigPanelProps> = ({ 
  agentId, 
  agentName,
  onConfigChange 
}) => {
  const [activeTab, setActiveTab] = useState<'console' | 'config'>('console');
  const [config, setConfig] = useState<AgentConfigData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);

  // Load agent configuration when switching to config tab
  useEffect(() => {
    if (activeTab === 'config' && !config) {
      loadAgentConfig();
    }
  }, [activeTab]);

  const loadAgentConfig = async () => {
    try {
      setIsLoading(true);
      const response = await fetch(`${API_BASE_URL}/api/config/export`);
      if (response.ok) {
        const rootConfig = await response.json();
        if (rootConfig.agents && rootConfig.agents[agentId]) {
          setConfig(rootConfig.agents[agentId]);
        }
      }
    } catch (error) {
      console.error('Error loading agent config:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleConfigChange = (field: string, value: string | number | boolean | Record<string, string | number | boolean>) => {
    if (!config) return;

    const updatedConfig = { ...config };
    const keys = field.split('.');
    
    // Navigate to nested property
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let current: any = updatedConfig;
    for (let i = 0; i < keys.length - 1; i++) {
      if (!current[keys[i]]) {
        current[keys[i]] = {};
      }
      current = current[keys[i]];
    }
    
    // Set the value
    current[keys[keys.length - 1]] = value;
    
    setConfig(updatedConfig);
    setHasChanges(true);
    
    // Notify parent
    if (onConfigChange) {
      onConfigChange(agentId, updatedConfig);
    }
  };

  const handleMarkAsApplied = () => {
    // Mark changes as applied - the parent component handles updating the full configuration
    // This is just a UI state update to clear the "has changes" indicator
    setHasChanges(false);
  };

  const handleResetChanges = () => {
    loadAgentConfig();
    setHasChanges(false);
  };

  return (
    <div className="flex flex-col h-full bg-gray-900 border-r border-gray-700">
      {/* Tab Header */}
      <div className="flex border-b border-gray-700 bg-gray-800">
        <button
          onClick={() => setActiveTab('console')}
          className={`flex-1 px-4 py-3 text-sm font-semibold transition-colors ${
            activeTab === 'console'
              ? 'text-white bg-gray-900 border-b-2 border-blue-500'
              : 'text-gray-400 hover:text-white hover:bg-gray-750'
          }`}
        >
          📊 Console
        </button>
        <button
          onClick={() => setActiveTab('config')}
          className={`flex-1 px-4 py-3 text-sm font-semibold transition-colors ${
            activeTab === 'config'
              ? 'text-white bg-gray-900 border-b-2 border-blue-500'
              : 'text-gray-400 hover:text-white hover:bg-gray-750'
          }`}
        >
          ⚙️ Config
        </button>
      </div>

      {/* Tab Content */}
      {activeTab === 'console' ? (
        <div className="flex-1 overflow-hidden">
          <AgentConsole agentId={agentId} agentName={agentName} />
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {isLoading ? (
            <div className="text-gray-400 text-center py-8">Loading configuration...</div>
          ) : !config ? (
            <div className="text-gray-400 text-center py-8">
              No configuration loaded. Please load a YAML configuration first.
            </div>
          ) : (
            <>
              {/* Agent Name */}
              <div>
                <label className="block text-xs font-semibold text-gray-400 mb-1">
                  Agent Name
                </label>
                <input
                  type="text"
                  value={config.name}
                  onChange={(e) => handleConfigChange('name', e.target.value)}
                  className="w-full px-3 py-2 text-sm bg-gray-800 text-white rounded border border-gray-700 focus:outline-none focus:border-blue-500"
                />
              </div>

              {/* Persona */}
              <div>
                <label className="block text-xs font-semibold text-gray-400 mb-1">
                  Persona / System Prompt
                </label>
                <textarea
                  value={config.persona}
                  onChange={(e) => handleConfigChange('persona', e.target.value)}
                  rows={6}
                  className="w-full px-3 py-2 text-sm bg-gray-800 text-white rounded border border-gray-700 focus:outline-none focus:border-blue-500 font-mono"
                  placeholder="Enter agent persona and instructions..."
                />
              </div>

              {/* Model Configuration */}
              <div className="border-t border-gray-700 pt-4">
                <h4 className="text-sm font-semibold text-white mb-3">Model Configuration</h4>
                
                <div className="space-y-3">
                  {/* Provider */}
                  <div>
                    <label className="block text-xs font-semibold text-gray-400 mb-1">
                      Provider
                    </label>
                    <input
                      type="text"
                      value={config.model.provider}
                      onChange={(e) => handleConfigChange('model.provider', e.target.value)}
                      className="w-full px-3 py-2 text-sm bg-gray-800 text-white rounded border border-gray-700 focus:outline-none focus:border-blue-500"
                    />
                  </div>

                  {/* URL */}
                  <div>
                    <label className="block text-xs font-semibold text-gray-400 mb-1">
                      API URL
                    </label>
                    <input
                      type="text"
                      value={config.model.url}
                      onChange={(e) => handleConfigChange('model.url', e.target.value)}
                      className="w-full px-3 py-2 text-sm bg-gray-800 text-white rounded border border-gray-700 focus:outline-none focus:border-blue-500"
                      placeholder="http://localhost:11434"
                    />
                  </div>

                  {/* Model Name */}
                  <div>
                    <label className="block text-xs font-semibold text-gray-400 mb-1">
                      Model Name
                    </label>
                    <input
                      type="text"
                      value={config.model.model_name}
                      onChange={(e) => handleConfigChange('model.model_name', e.target.value)}
                      className="w-full px-3 py-2 text-sm bg-gray-800 text-white rounded border border-gray-700 focus:outline-none focus:border-blue-500"
                      placeholder="llama2, mistral, etc."
                    />
                  </div>

                  {/* Thinking Mode */}
                  <div className="flex items-center">
                    <input
                      type="checkbox"
                      id={`thinking-${agentId}`}
                      checked={config.model.thinking}
                      onChange={(e) => handleConfigChange('model.thinking', e.target.checked)}
                      className="mr-2"
                    />
                    <label htmlFor={`thinking-${agentId}`} className="text-xs text-gray-400">
                      Enable Thinking Mode (separate internal reasoning)
                    </label>
                  </div>

                  {/* Temperature */}
                  <div>
                    <label className="block text-xs font-semibold text-gray-400 mb-1">
                      Temperature: {config.model.parameters.temperature?.toFixed(2) ?? '0.70'}
                    </label>
                    <input
                      type="range"
                      min="0"
                      max="2"
                      step="0.01"
                      value={config.model.parameters.temperature ?? 0.7}
                      onChange={(e) => handleConfigChange('model.parameters.temperature', parseFloat(e.target.value))}
                      className="w-full"
                    />
                  </div>

                  {/* Top P */}
                  <div>
                    <label className="block text-xs font-semibold text-gray-400 mb-1">
                      Top P: {config.model.parameters.top_p?.toFixed(2) ?? '0.90'}
                    </label>
                    <input
                      type="range"
                      min="0"
                      max="1"
                      step="0.01"
                      value={config.model.parameters.top_p ?? 0.9}
                      onChange={(e) => handleConfigChange('model.parameters.top_p', parseFloat(e.target.value))}
                      className="w-full"
                    />
                  </div>
                </div>
              </div>

              {/* MCP Servers */}
              <div className="border-t border-gray-700 pt-4">
                <h4 className="text-sm font-semibold text-white mb-2">MCP Servers</h4>
                <div className="text-xs text-gray-400">
                  {config.mcp_servers.length === 0 ? (
                    <span>No agent-specific MCP servers configured</span>
                  ) : (
                    <ul className="list-disc list-inside">
                      {config.mcp_servers.map((server, idx) => (
                        <li key={idx}>{server}</li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>

              {/* Action Buttons */}
              {hasChanges && (
                <div className="flex space-x-2 border-t border-gray-700 pt-4">
                  <button
                    onClick={handleMarkAsApplied}
                    className="flex-1 px-3 py-2 text-sm bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors"
                    title="Mark changes as applied. Use 'Download w/ Changes' button to export."
                  >
                    ✓ Mark as Applied
                  </button>
                  <button
                    onClick={handleResetChanges}
                    className="flex-1 px-3 py-2 text-sm bg-gray-700 hover:bg-gray-600 text-white rounded transition-colors"
                  >
                    ↺ Reset
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
};

export default AgentConfigPanel;
