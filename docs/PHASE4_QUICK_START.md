# Phase 4 Quick Start Guide

## Overview

Phase 4 adds a complete web interface with real-time features for the AI Agent Mixer platform. This guide will help you get started with the new features.

## Prerequisites

- Backend running on `http://localhost:8000`
- Frontend running on `http://localhost:5173`
- Ollama instance available (optional, for testing connections)

## Quick Start Steps

### 1. Start the Application

**Backend:**
```bash
cd backend
uv run uvicorn app.main:app --reload
```

**Frontend:**
```bash
cd frontend
npm run dev
```

### 2. Load a Configuration

1. Open `http://localhost:5173` in your browser
2. Expand the Configuration Panel at the bottom
3. Click "📁 Load File" and select `config/example-simple.yaml`
4. Or drag-and-drop the YAML file onto the editor
5. Click "✓ Validate" to check the configuration
6. Click "⚡ Apply" to load it into the backend

### 3. Test Connections (Optional)

If you have Ollama running:
1. Click "🔌 Test Connections"
2. Wait for the results to appear
3. Green checkmarks indicate successful connections
4. Red X marks indicate connection failures

### 4. Start a Conversation

1. In the Control Panel at the top:
   - Set "Max Cycles" (default: 5)
   - Choose "Starting Agent" (agent_a or agent_b)
2. Click "▶️ Start" button
3. Watch the conversation unfold in real-time!

### 5. Monitor the Conversation

- **Left Console (Agent A)**: See Agent A's internal thoughts
- **Center Panel**: See the actual conversation messages
- **Right Console (Agent B)**: See Agent B's internal thoughts
- **Progress Bar**: Track cycle completion
- **Status Indicator**: Shows current state (Running, Paused, etc.)

### 6. Control the Conversation

- **⏸️ Pause**: Pause the conversation
- **▶️ Resume**: Resume a paused conversation
- **⏹️ Stop**: Terminate the conversation

### 7. Export Your Work

**Export Conversation:**
1. Click "📥 Export" in the Conversation Exchange
2. A markdown file will download with the full conversation

**Export Configuration:**
1. Click "💾 Export" in the Configuration Panel
2. A YAML file will download with your configuration

## Features in Detail

### Agent Console (Left & Right)

- Real-time streaming of agent thoughts
- Timestamped messages
- Auto-scroll (pauses when you scroll up)
- "Jump to bottom" button
- Clear console button
- Performance optimized for 1000+ messages

### Conversation Exchange (Center)

- Alternating colored message bubbles
  - Blue: Agent A
  - Green: Agent B
- Shows agent name, timestamp, and cycle number
- Yellow ring highlights current turn
- Export to markdown
- Pause/Resume controls

### Configuration Editor (Bottom)

- Monaco Editor with YAML syntax highlighting
- Real-time validation
- Ollama connection testing
- MCP server health indicators
- Drag-and-drop file import
- File picker import
- Export to YAML

### Control Panel (Top)

- Start/Stop/Pause/Resume buttons
- Status indicator with animations
- Progress tracking
  - Current cycle / Max cycles
  - Message count
  - Progress bar
- Configuration overrides
  - Max cycles (1-100)
  - Starting agent selection

## WebSocket Events

The application uses WebSocket for real-time updates:

- **connection**: Connection status
- **thought**: Agent internal thoughts
- **conversation_message**: Conversation messages
- **turn_indicator**: Current turn indicator
- **conversation_started**: Conversation started
- **conversation_ended**: Conversation completed
- **conversation_status**: Status updates (paused/resumed)
- **conversation_error**: Error notifications

## API Endpoints

### Configuration Management
- `GET /api/config/schema` - Get JSON schema
- `POST /api/config/validate` - Validate YAML
- `POST /api/config/import` - Import configuration
- `GET /api/config/export` - Export configuration
- `POST /api/config/upload` - Upload YAML file

### Conversation Control
- `POST /api/conversation/start` - Start conversation
- `POST /api/conversation/stop` - Stop conversation
- `POST /api/conversation/pause` - Pause conversation
- `POST /api/conversation/resume` - Resume conversation
- `GET /api/conversation/status` - Get status

### Ollama Testing
- `POST /api/ollama/test-connection` - Test Ollama connection

### MCP Server Management
- `GET /api/mcp/status` - Get all server status
- `GET /api/mcp/servers/{name}/status` - Get specific server status
- `POST /api/mcp/servers/{name}/restart` - Restart server
- `GET /api/mcp/tools` - Get all tools
- `GET /api/mcp/agents/{id}/tools` - Get agent tools

## Troubleshooting

### Frontend Won't Connect
- Check that backend is running on port 8000
- Check browser console for WebSocket errors
- Verify CORS is enabled in backend

### Configuration Won't Apply
- Validate the YAML first
- Check for validation errors
- Ensure all required fields are present

### Conversation Won't Start
- Ensure configuration is loaded and applied
- Check that config_loaded is true in /health endpoint
- Verify Ollama is running if testing connections

### No Messages Appearing
- Check WebSocket connection status (should show "Connected")
- Verify backend is sending WebSocket events
- Check browser console for errors

### MCP Servers Not Starting
- Check that MCP server commands are correct
- Verify npx is available if using npm-based MCP servers
- Check backend logs for MCP startup errors

## Tips & Tricks

1. **Quick Configuration Loading**: Drag-and-drop is the fastest way to load a config
2. **Watch the Status**: The colored dot tells you exactly what state you're in
3. **Scroll Detection**: Consoles auto-scroll unless you manually scroll up
4. **Export Early**: Export your conversation as you go to save progress
5. **Test Connections First**: Verify Ollama connectivity before starting
6. **Use Validation**: Always validate before applying to catch errors early

## Example Configuration

Here's a minimal working configuration:

```yaml
version: "1.0"

metadata:
  name: "Simple Test"
  description: "Basic conversation"

conversation:
  starting_agent: "agent_a"
  max_cycles: 3
  turn_timeout: 120
  termination_conditions:
    keyword_triggers: ["goodbye"]
    silence_detection: 2

agents:
  agent_a:
    name: "Agent A"
    persona: "You are a friendly AI."
    model:
      provider: "ollama"
      url: "http://localhost:11434"
      model_name: "llama2"
      thinking: false
      parameters:
        temperature: 0.7
    mcp_servers: []

  agent_b:
    name: "Agent B"
    persona: "You are a helpful AI."
    model:
      provider: "ollama"
      url: "http://localhost:11434"
      model_name: "llama2"
      thinking: false
      parameters:
        temperature: 0.7
    mcp_servers: []

mcp_servers:
  global_servers: []

initialization:
  system_prompt_template: |
    You are {{ agent.name }}.
    {{ agent.persona }}
  first_message: "Hello! Let's have a brief conversation."

logging:
  level: "INFO"
  include_thoughts: true
  output_directory: null
```

## Next Steps

- Experiment with different agent personas
- Try enabling thinking mode for agents
- Add MCP servers for tool use
- Adjust max_cycles and termination conditions
- Export and share your conversations

## Support

For issues or questions:
1. Check the browser console for errors
2. Check the backend logs
3. Verify configuration is valid
4. Review the PHASE4_SUMMARY.md for detailed documentation

Enjoy your AI Agent Mixer! 🚀
