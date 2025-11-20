import React, { useState } from 'react';

const ConfigurationPanel: React.FC = () => {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [configText, setConfigText] = useState('');

  return (
    <div
      className={`transition-all duration-300 bg-gray-900 border-t border-gray-700 ${
        isCollapsed ? 'h-12' : 'h-64'
      }`}
    >
      {/* Header */}
      <div className="flex justify-between items-center p-3 border-b border-gray-700">
        <h3 className="text-sm font-semibold text-white">Configuration</h3>
        <button
          onClick={() => setIsCollapsed(!isCollapsed)}
          className="px-2 py-1 text-xs bg-gray-700 hover:bg-gray-600 text-white rounded transition-colors"
        >
          {isCollapsed ? '▲ Expand' : '▼ Collapse'}
        </button>
      </div>

      {/* Content */}
      {!isCollapsed && (
        <div className="p-4 h-[calc(100%-48px)] flex flex-col space-y-2">
          <div className="flex space-x-2">
            <button className="px-3 py-1 text-xs bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors">
              Load Config
            </button>
            <button className="px-3 py-1 text-xs bg-green-600 hover:bg-green-700 text-white rounded transition-colors">
              Validate
            </button>
            <button className="px-3 py-1 text-xs bg-purple-600 hover:bg-purple-700 text-white rounded transition-colors">
              Apply
            </button>
          </div>

          <textarea
            value={configText}
            onChange={(e) => setConfigText(e.target.value)}
            placeholder="Load or paste YAML configuration here..."
            className="flex-1 w-full bg-gray-800 text-white text-sm font-mono p-2 rounded border border-gray-700 focus:border-blue-500 focus:outline-none resize-none"
          />

          <div className="text-xs text-gray-400">
            Status: <span className="text-yellow-400">No configuration loaded</span>
          </div>
        </div>
      )}
    </div>
  );
};

export default ConfigurationPanel;
