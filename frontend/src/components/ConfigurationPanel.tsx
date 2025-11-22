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

const ConfigurationPanel: React.FC<ConfigurationPanelProps> = ({ 
  onConfigApplied,
  agentConfigChanges = {}
}) => {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [configText, setConfigText] = useState('');
  const [validationErrors, setValidationErrors] = useState<ValidationError[]>([]);
  const [validationStatus, setValidationStatus] = useState<'idle' | 'validating' | 'valid' | 'invalid'>('idle');
  const [mcpStatus, setMcpStatus] = useState<Record<string, MCPServerStatus>>({});
  const [connectionTestResults, setConnectionTestResults] = useState<Record<string, any>>({});
  const [isTestingConnections, setIsTestingConnections] = useState(false);

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
      const config = yaml.load(configText) as any;
      
      // Apply agent config changes
      if (config.agents && Object.keys(agentConfigChanges).length > 0) {
        for (const [agentId, agentConfig] of Object.entries(agentConfigChanges)) {
          if (config.agents[agentId]) {
            config.agents[agentId] = agentConfig;
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
      {/* Header */}
      <div className="flex justify-between items-center p-3 border-b border-gray-700">
        <h3 className="text-sm font-semibold text-white">Configuration Editor</h3>
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
        <div className="p-4 h-[calc(100%-48px)] flex flex-col space-y-2">
          {/* Buttons */}
          <div className="flex space-x-2 items-center">
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
    </div>
  );
};

export default ConfigurationPanel;
