import React from 'react';
import AgentConsole from './components/AgentConsole';
import ConversationExchange from './components/ConversationExchange';
import ConfigurationPanel from './components/ConfigurationPanel';

const App: React.FC = () => {
  return (
    <div className="flex flex-col h-screen bg-gray-900">
      {/* Header */}
      <header className="bg-gray-950 border-b border-gray-700 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <h1 className="text-2xl font-bold text-white">
              🤖 AI Agent Mixer
            </h1>
            <span className="px-2 py-1 text-xs bg-green-600 text-white rounded">
              Ready
            </span>
          </div>
          <div className="flex space-x-2">
            <button className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors">
              Start Conversation
            </button>
            <button className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded transition-colors">
              Settings
            </button>
          </div>
        </div>
      </header>

      {/* Main content - Three column layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left column - Agent A Console */}
        <div className="w-1/4 min-w-[300px] max-w-[400px] hidden lg:block">
          <AgentConsole agentId="agent_a" agentName="Agent A" />
        </div>

        {/* Center column - Conversation Exchange */}
        <div className="flex-1 min-w-0">
          <ConversationExchange />
        </div>

        {/* Right column - Agent B Console */}
        <div className="w-1/4 min-w-[300px] max-w-[400px] hidden lg:block">
          <AgentConsole agentId="agent_b" agentName="Agent B" />
        </div>
      </div>

      {/* Bottom panel - Configuration */}
      <ConfigurationPanel />
    </div>
  );
};

export default App;
