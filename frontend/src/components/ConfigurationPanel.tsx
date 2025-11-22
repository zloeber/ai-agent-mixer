import React, { useState, useEffect } from 'react';
import Editor from '@monaco-editor/react';
import * as yaml from 'js-yaml';
import { AgentConfigData } from './AgentConfigPanel';

interface ConfigurationPanelProps {
  onConfigApplied?: () => void;
  agentConfigChanges?: Record<string, AgentConfigData>;
}

interface ValidationError {
  location: string;
  message: string;
}

interface MCPServerStatus {
  running: boolean;
  healthy: boolean;
}

interface ConversationScenario {
  name: string;
  goal?: string;
  brevity: string;
  starting_agent: string;
  max_cycles: number;
  turn_timeout: number;
  agents_involved?: string[];
}

interface MCPServerConfig {
  name: string;
  command: string;
  args?: string[];
  env?: Record<string, string>;
}

interface AgentConfig {
  name: string;
  persona: string;
  mcp_servers?: string[];
  metadata?: Record<string, unknown>;
}

interface LoadedConfig {
  agents?: Record<string, AgentConfig>;
  initialization?: {
    first_message?: string;
    system_prompt_template?: string;
  };
  conversations?: ConversationScenario[];
  conversation?: {
    starting_agent: string;
    max_cycles: number;
    turn_timeout: number;
  };
  mcp_servers?: {
    global_servers?: MCPServerConfig[];
  };
  logging?: {
    level: string;
    include_thoughts: boolean;
    output_directory?: string;
  };
}

const ConfigurationPanel: React.FC<ConfigurationPanelProps> = ({ 
  onConfigApplied,
  agentConfigChanges = {}
}) => {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [activeTab, setActiveTab] = useState<'editor' | 'initialization' | 'conversations' | 'mcp' | 'logging'>('editor');
  const [configText, setConfigText] = useState('');
  const [validationErrors, setValidationErrors] = useState<ValidationError[]>([]);
  const [validationStatus, setValidationStatus] = useState<'idle' | 'validating' | 'valid' | 'invalid'>('idle');
  const [mcpStatus, setMcpStatus] = useState<Record<string, MCPServerStatus>>({});
  const [connectionTestResults, setConnectionTestResults] = useState<Record<string, any>>({});
  const [isTestingConnections, setIsTestingConnections] = useState(false);
  const [loadedConfig, setLoadedConfig] = useState<LoadedConfig | null>(null);

  // Fetch JSON schema for autocomplete
  useEffect(() => {
    const fetchSchema = async () => {
      try {
        const response = await fetch('http://localhost:8000/api/config/schema');
        if (response.ok) {
          await response.json();
          // Monaco will use this for autocomplete (configured in Editor component)
          console.log('Schema loaded successfully');
        }
      } catch (error) {
        console.error('Error loading schema:', error);
      }
    };
    
    fetchSchema();
  }, []);

  // Fetch MCP server status periodically
  useEffect(() => {
    const fetchMcpStatus = async () => {
      try {
        const response = await fetch('http://localhost:8000/api/mcp/status');
        if (response.ok) {
          const data = await response.json();
          const statusMap: Record<string, MCPServerStatus> = {};
          for (const [name, status] of Object.entries(data.servers)) {
            const s = status as any;
            statusMap[name] = {
              running: s.running,
              healthy: s.healthy
            };
          }
          setMcpStatus(statusMap);
        }
      } catch (error) {
        console.error('Error fetching MCP status:', error);
      }
    };

    fetchMcpStatus();
    const interval = setInterval(fetchMcpStatus, 5000); // Update every 5 seconds

    return () => clearInterval(interval);
  }, []);

  // Load current config for display tabs
  useEffect(() => {
    const loadConfig = async () => {
      try {
        const response = await fetch('http://localhost:8000/api/config/export');
        if (response.ok) {
          const config = await response.json();
          setLoadedConfig(config);
        }
      } catch (error) {
        console.error('Error loading config:', error);
      }
    };

    loadConfig();
    const interval = setInterval(loadConfig, 3000); // Refresh every 3 seconds

    return () => clearInterval(interval);
  }, []);

  const handleValidate = async () => {
    setValidationStatus('validating');
    setValidationErrors([]);

    try {
      const response = await fetch('http://localhost:8000/api/config/validate', {
        method: 'POST',
        headers: { 'Content-Type': 'text/plain' },
        body: configText
      });

      const data = await response.json();

      if (data.valid) {
        setValidationStatus('valid');
      } else {
        setValidationStatus('invalid');
        setValidationErrors(data.errors || []);
      }
    } catch (error) {
      setValidationStatus('invalid');
      setValidationErrors([{ location: 'network', message: 'Failed to validate configuration' }]);
    }
  };

  const handleTestConnections = async () => {
    setIsTestingConnections(true);
    setConnectionTestResults({});

    try {
      // Parse YAML to get agent configurations
      const config = yaml.load(configText) as any;

      const results: Record<string, any> = {};

      if (config.agents) {
        for (const [agentId, agentConfig] of Object.entries(config.agents)) {
          const agent = agentConfig as any;
          if (agent.model) {
            try {
              const response = await fetch('http://localhost:8000/api/ollama/test-connection', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(agent.model)
              });

              results[agentId] = await response.json();
            } catch (error) {
              results[agentId] = {
                status: 'error',
                message: 'Connection failed'
              };
            }
          }
        }
      }

      setConnectionTestResults(results);
    } catch (error) {
      console.error('Error testing connections:', error);
    } finally {
      setIsTestingConnections(false);
    }
  };

  const handleApply = async () => {
    try {
      const configDict = yaml.load(configText);

      const response = await fetch('http://localhost:8000/api/config/import', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(configDict)
      });

      if (response.ok) {
        const data = await response.json();
        console.log('Configuration applied:', data);
        setValidationStatus('valid');
        setValidationErrors([]);
        if (onConfigApplied) {
          onConfigApplied();
        }
      } else {
        const errorData = await response.json();
        setValidationStatus('invalid');
        setValidationErrors(errorData.errors || [{ location: 'import', message: errorData.detail }]);
      }
    } catch (error: any) {
      setValidationStatus('invalid');
      setValidationErrors([{ location: 'import', message: error.message }]);
    }
  };

  const handleLoadFile = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      const text = await file.text();
      setConfigText(text);
      setValidationStatus('idle');
      setValidationErrors([]);
    }
  };

  const handleDrop = async (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    const file = event.dataTransfer.files[0];
    if (file && (file.name.endsWith('.yaml') || file.name.endsWith('.yml'))) {
      const text = await file.text();
      setConfigText(text);
      setValidationStatus('idle');
      setValidationErrors([]);
    }
  };

  const handleExport = () => {
    const blob = new Blob([configText], { type: 'text/yaml' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `config-${Date.now()}.yaml`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleDownloadWithChanges = () => {
    try {
      // Parse current YAML
      const config = yaml.load(configText) as Record<string, unknown>;
      
      // Apply agent config changes
      if (config.agents && typeof config.agents === 'object' && Object.keys(agentConfigChanges).length > 0) {
        const agents = config.agents as Record<string, unknown>;
        for (const [agentId, agentConfig] of Object.entries(agentConfigChanges)) {
          if (agents[agentId]) {
            agents[agentId] = agentConfig;
          }
        }
      }
      
      // Convert back to YAML
      const updatedYaml = yaml.dump(config, {
        lineWidth: -1, // Don't wrap lines
        noRefs: true,
        sortKeys: false
      });
      
      // Download
      const blob = new Blob([updatedYaml], { type: 'text/yaml' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `config-updated-${Date.now()}.yaml`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Error generating updated config:', error);
      alert('Failed to generate updated configuration');
    }
  };

  return (
    <div
      className={`transition-all duration-300 bg-gray-900 border-t border-gray-700 ${
        isCollapsed ? 'h-12' : 'h-96'
      }`}
    >
      {/* Header with tabs */}
      <div className="flex justify-between items-center p-3 border-b border-gray-700">
        <div className="flex space-x-1">
          <button
            onClick={() => setActiveTab('editor')}
            className={`px-3 py-1 text-xs rounded transition-colors ${
              activeTab === 'editor'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
            }`}
          >
            📝 YAML Editor
          </button>
          <button
            onClick={() => setActiveTab('initialization')}
            className={`px-3 py-1 text-xs rounded transition-colors ${
              activeTab === 'initialization'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
            }`}
          >
            🚀 Initialization
          </button>
          <button
            onClick={() => setActiveTab('conversations')}
            className={`px-3 py-1 text-xs rounded transition-colors ${
              activeTab === 'conversations'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
            }`}
          >
            💬 Conversations
          </button>
          <button
            onClick={() => setActiveTab('mcp')}
            className={`px-3 py-1 text-xs rounded transition-colors ${
              activeTab === 'mcp'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
            }`}
          >
            🔧 MCP Servers
          </button>
          <button
            onClick={() => setActiveTab('logging')}
            className={`px-3 py-1 text-xs rounded transition-colors ${
              activeTab === 'logging'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
            }`}
          >
            📋 Logging
          </button>
        </div>
        <div className="flex items-center space-x-2">
          {/* MCP Server Status Indicators */}
          {Object.keys(mcpStatus).length > 0 && (
            <div className="flex items-center space-x-2 mr-4">
              <span className="text-xs text-gray-400">MCP Servers:</span>
              {Object.entries(mcpStatus).map(([name, status]) => (
                <div
                  key={name}
                  className="flex items-center space-x-1"
                  title={`${name}: ${status.healthy ? 'Healthy' : 'Unhealthy'}`}
                >
                  <div
                    className={`w-2 h-2 rounded-full ${
                      status.healthy ? 'bg-green-500' : 'bg-red-500'
                    }`}
                  />
                  <span className="text-xs text-gray-400">{name}</span>
                </div>
              ))}
            </div>
          )}
          <button
            onClick={() => setIsCollapsed(!isCollapsed)}
            className="px-2 py-1 text-xs bg-gray-700 hover:bg-gray-600 text-white rounded transition-colors"
          >
            {isCollapsed ? '▲ Expand' : '▼ Collapse'}
          </button>
        </div>
      </div>

      {/* Content */}
      {!isCollapsed && (
        <div className="p-4 h-[calc(100%-48px)] overflow-y-auto">
          {/* YAML Editor Tab */}
          {activeTab === 'editor' && (
            <div className="h-full flex flex-col space-y-2">
              {/* Buttons */}
              <div className="flex space-x-2 items-center flex-wrap">
                <label className="px-3 py-1 text-xs bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors cursor-pointer">
                  📁 Load File
                  <input
                    type="file"
                    accept=".yaml,.yml"
                    onChange={handleLoadFile}
                    className="hidden"
                  />
                </label>
                <button
                  onClick={handleValidate}
                  className="px-3 py-1 text-xs bg-green-600 hover:bg-green-700 text-white rounded transition-colors disabled:opacity-50"
                  disabled={!configText || validationStatus === 'validating'}
                >
                  ✓ Validate
                </button>
                <button
                  onClick={handleTestConnections}
                  className="px-3 py-1 text-xs bg-purple-600 hover:bg-purple-700 text-white rounded transition-colors disabled:opacity-50"
                  disabled={!configText || isTestingConnections}
                >
                  {isTestingConnections ? '⏳ Testing...' : '🔌 Test Connections'}
                </button>
                <button
                  onClick={handleApply}
                  className="px-3 py-1 text-xs bg-orange-600 hover:bg-orange-700 text-white rounded transition-colors disabled:opacity-50"
                  disabled={!configText || validationStatus === 'invalid'}
                >
                  ⚡ Apply
                </button>
                <button
                  onClick={handleExport}
                  className="px-3 py-1 text-xs bg-gray-600 hover:bg-gray-700 text-white rounded transition-colors disabled:opacity-50"
                  disabled={!configText}
                >
                  💾 Export
                </button>
                
                {/* Download with Agent Changes button - only show if there are changes */}
                {Object.keys(agentConfigChanges).length > 0 && (
                  <button
                    onClick={handleDownloadWithChanges}
                    className="px-3 py-1 text-xs bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors disabled:opacity-50 animate-pulse"
                    disabled={!configText}
                    title="Download YAML with agent configuration changes"
                  >
                    ⬇️ Download w/ Changes
                  </button>
                )}
                
                {/* Validation Status */}
                {validationStatus !== 'idle' && (
                  <div className="ml-auto text-xs">
                    {validationStatus === 'validating' && (
                      <span className="text-yellow-400">⏳ Validating...</span>
                    )}
                    {validationStatus === 'valid' && (
                      <span className="text-green-400">✓ Valid</span>
                    )}
                    {validationStatus === 'invalid' && (
                      <span className="text-red-400">✗ Invalid</span>
                    )}
                  </div>
                )}
              </div>

              {/* Editor */}
              <div
                className="flex-1 border border-gray-700 rounded overflow-hidden"
                onDrop={handleDrop}
                onDragOver={(e) => e.preventDefault()}
              >
                <Editor
                  height="100%"
                  defaultLanguage="yaml"
                  value={configText}
                  onChange={(value) => {
                    setConfigText(value || '');
                    setValidationStatus('idle');
                  }}
                  theme="vs-dark"
                  options={{
                    minimap: { enabled: false },
                    fontSize: 12,
                    lineNumbers: 'on',
                    scrollBeyondLastLine: false,
                    wordWrap: 'on',
                    automaticLayout: true,
                  }}
                />
              </div>

              {/* Validation Errors */}
              {validationErrors.length > 0 && (
                <div className="p-2 bg-red-900 bg-opacity-30 border border-red-700 rounded text-xs space-y-1 max-h-24 overflow-y-auto">
                  {validationErrors.map((error, idx) => (
                    <div key={idx} className="text-red-400">
                      <span className="font-semibold">{error.location}:</span> {error.message}
                    </div>
                  ))}
                </div>
              )}

              {/* Connection Test Results */}
              {Object.keys(connectionTestResults).length > 0 && (
                <div className="p-2 border border-gray-700 rounded text-xs space-y-1 max-h-24 overflow-y-auto">
                  {Object.entries(connectionTestResults).map(([agentId, result]) => (
                    <div key={agentId} className="flex items-center space-x-2">
                      <span className="text-gray-400">{agentId}:</span>
                      {result.status === 'success' ? (
                        <span className="text-green-400">✓ Connected</span>
                      ) : (
                        <span className="text-red-400">✗ {result.message}</span>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {/* Help Text */}
              <div className="text-xs text-gray-500">
                {configText ? (
                  <span>Drag & drop or load a YAML file. Validate before applying.</span>
                ) : (
                  <span>💡 Load or paste YAML configuration here. Drag & drop supported.</span>
                )}
              </div>
            </div>
          )}

          {/* Initialization Tab */}
          {activeTab === 'initialization' && (
            <div className="space-y-3 text-sm">
              {loadedConfig && loadedConfig.initialization ? (
                <>
                  <div>
                    <h4 className="text-white font-semibold mb-2">First Message</h4>
                    <div className="bg-gray-800 p-3 rounded border border-gray-700 text-gray-300 whitespace-pre-wrap">
                      {loadedConfig.initialization.first_message}
                    </div>
                  </div>
                  
                  {loadedConfig.initialization.system_prompt_template && (
                    <div>
                      <h4 className="text-white font-semibold mb-2">System Prompt Template</h4>
                      <div className="bg-gray-800 p-3 rounded border border-gray-700 text-gray-300 whitespace-pre-wrap font-mono text-xs">
                        {loadedConfig.initialization.system_prompt_template}
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <div className="text-gray-400 text-center py-8">
                  No initialization configuration loaded
                </div>
              )}
            </div>
          )}

          {/* Conversations Tab */}
          {activeTab === 'conversations' && (
            <div className="space-y-3 text-sm">
              {loadedConfig && (loadedConfig.conversations || loadedConfig.conversation) ? (
                <>
                  {loadedConfig.conversations && (
                    <div>
                      <h4 className="text-white font-semibold mb-2">Available Scenarios</h4>
                      <div className="space-y-2">
                        {loadedConfig.conversations.map((conv: ConversationScenario, idx: number) => (
                          <div key={idx} className="bg-gray-800 p-3 rounded border border-gray-700">
                            <div className="font-semibold text-white mb-1">{conv.name}</div>
                            {conv.goal && <div className="text-gray-400 text-xs mb-2">{conv.goal}</div>}
                            <div className="grid grid-cols-2 gap-2 text-xs">
                              <div><span className="text-gray-500">Starting Agent:</span> <span className="text-blue-400">{conv.starting_agent}</span></div>
                              <div><span className="text-gray-500">Max Cycles:</span> <span className="text-blue-400">{conv.max_cycles}</span></div>
                              <div><span className="text-gray-500">Brevity:</span> <span className="text-blue-400">{conv.brevity}</span></div>
                              <div><span className="text-gray-500">Timeout:</span> <span className="text-blue-400">{conv.turn_timeout}s</span></div>
                            </div>
                            {conv.agents_involved && (
                              <div className="mt-2 text-xs">
                                <span className="text-gray-500">Agents:</span> {conv.agents_involved.join(', ')}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  {loadedConfig.conversation && !loadedConfig.conversations && (
                    <div>
                      <h4 className="text-white font-semibold mb-2">Legacy Conversation Configuration</h4>
                      <div className="bg-gray-800 p-3 rounded border border-gray-700">
                        <div className="grid grid-cols-2 gap-2 text-xs">
                          <div><span className="text-gray-500">Starting Agent:</span> <span className="text-blue-400">{loadedConfig.conversation.starting_agent}</span></div>
                          <div><span className="text-gray-500">Max Cycles:</span> <span className="text-blue-400">{loadedConfig.conversation.max_cycles}</span></div>
                          <div><span className="text-gray-500">Timeout:</span> <span className="text-blue-400">{loadedConfig.conversation.turn_timeout}s</span></div>
                        </div>
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <div className="text-gray-400 text-center py-8">
                  No conversation configuration loaded
                </div>
              )}
            </div>
          )}

          {/* MCP Servers Tab */}
          {activeTab === 'mcp' && (
            <div className="space-y-3 text-sm">
              {loadedConfig && loadedConfig.mcp_servers ? (
                <>
                  <div>
                    <h4 className="text-white font-semibold mb-2">Global MCP Servers</h4>
                    {loadedConfig.mcp_servers.global_servers && loadedConfig.mcp_servers.global_servers.length > 0 ? (
                      <div className="space-y-2">
                        {loadedConfig.mcp_servers.global_servers.map((server: MCPServerConfig, idx: number) => (
                          <div key={idx} className="bg-gray-800 p-3 rounded border border-gray-700">
                            <div className="flex items-center justify-between mb-2">
                              <span className="font-semibold text-white">{server.name}</span>
                              {mcpStatus[server.name] && (
                                <div className="flex items-center space-x-1">
                                  <div className={`w-2 h-2 rounded-full ${mcpStatus[server.name].healthy ? 'bg-green-500' : 'bg-red-500'}`} />
                                  <span className="text-xs text-gray-400">
                                    {mcpStatus[server.name].healthy ? 'Healthy' : 'Unhealthy'}
                                  </span>
                                </div>
                              )}
                            </div>
                            <div className="text-xs text-gray-400 font-mono">
                              <div><span className="text-gray-500">Command:</span> {server.command}</div>
                              {server.args && server.args.length > 0 && (
                                <div><span className="text-gray-500">Args:</span> {server.args.join(' ')}</div>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="text-gray-400 text-center py-4">No global MCP servers configured</div>
                    )}
                  </div>

                  <div>
                    <h4 className="text-white font-semibold mb-2">Agent-Specific MCP Servers</h4>
                    {loadedConfig.agents && Object.keys(loadedConfig.agents).some((agentId: string) => {
                      const agent = loadedConfig.agents?.[agentId];
                      return agent && agent.mcp_servers && agent.mcp_servers.length > 0;
                    }) ? (
                      <div className="space-y-2">
                        {loadedConfig.agents && Object.entries(loadedConfig.agents).map(([agentId, agent]: [string, AgentConfig]) => (
                          agent.mcp_servers && agent.mcp_servers.length > 0 && (
                            <div key={agentId} className="bg-gray-800 p-3 rounded border border-gray-700">
                              <div className="font-semibold text-white mb-1">{agent.name} ({agentId})</div>
                              <div className="text-xs text-gray-400">
                                MCP Servers: {agent.mcp_servers.join(', ')}
                              </div>
                            </div>
                          )
                        ))}
                      </div>
                    ) : (
                      <div className="text-gray-400 text-center py-4">No agent-specific MCP servers configured</div>
                    )}
                  </div>
                </>
              ) : (
                <div className="text-gray-400 text-center py-8">
                  No MCP server configuration loaded
                </div>
              )}
            </div>
          )}

          {/* Logging Tab */}
          {activeTab === 'logging' && (
            <div className="space-y-3 text-sm">
              {loadedConfig && loadedConfig.logging ? (
                <div className="bg-gray-800 p-4 rounded border border-gray-700">
                  <h4 className="text-white font-semibold mb-3">Logging Configuration</h4>
                  <div className="space-y-2 text-xs">
                    <div className="flex items-center justify-between">
                      <span className="text-gray-400">Log Level:</span>
                      <span className="text-blue-400 font-semibold">{loadedConfig.logging.level}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-gray-400">Include Thoughts:</span>
                      <span className={loadedConfig.logging.include_thoughts ? 'text-green-400' : 'text-red-400'}>
                        {loadedConfig.logging.include_thoughts ? '✓ Yes' : '✗ No'}
                      </span>
                    </div>
                    {loadedConfig.logging.output_directory && (
                      <div className="flex items-center justify-between">
                        <span className="text-gray-400">Output Directory:</span>
                        <span className="text-blue-400 font-mono">{loadedConfig.logging.output_directory}</span>
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                <div className="text-gray-400 text-center py-8">
                  No logging configuration loaded
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ConfigurationPanel;
