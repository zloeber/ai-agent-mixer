# Architecture Overview

## System Design

The Synthetic AI Conversation Orchestrator is built using a modern, modular architecture that separates concerns between configuration, orchestration, agent execution, and user interface.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Web Interface (React)                    │
│  ┌───────────┐  ┌──────────────┐  ┌───────────┐            │
│  │ Agent A   │  │ Conversation │  │ Agent B   │            │
│  │ Console   │  │   Exchange   │  │ Console   │            │
│  │ (Left)    │  │   (Center)   │  │ (Right)   │            │
│  └─────┬─────┘  └──────┬───────┘  └─────┬─────┘            │
│        │               │                │                   │
│        └───────────────┼────────────────┘                   │
│                        │ WebSocket                          │
└────────────────────────┼────────────────────────────────────┘
                         │
┌────────────────────────┼────────────────────────────────────┐
│             FastAPI Backend Service                         │
│                        │                                    │
│  ┌────────────────────▼──────────────────────┐             │
│  │     WebSocket Manager                      │             │
│  │  - Real-time message streaming             │             │
│  │  - Connection lifecycle management         │             │
│  └────────────────────────────────────────────┘             │
│                                                              │
│  ┌─────────────────────────────────────────────┐            │
│  │     Configuration Manager                   │            │
│  │  - YAML import/export                       │            │
│  │  - Environment variable substitution        │            │
│  │  - Pydantic validation                      │            │
│  └─────────────────────────────────────────────┘            │
│                                                              │
│  ┌─────────────────────────────────────────────┐            │
│  │     Conversation Orchestrator (LangGraph)   │            │
│  │  ├─ State Graph Management                  │            │
│  │  ├─ Agent Node Execution                    │            │
│  │  ├─ Tool Node Integration                   │            │
│  │  ├─ Cycle Detection & Termination           │            │
│  │  └─ Checkpoint System (persistence)         │            │
│  └─────────────────────────────────────────────┘            │
│                                                              │
│  ┌─────────────────────────────────────────────┐            │
│  │     MCP Server Manager                      │            │
│  │  - Server lifecycle (start/stop/restart)    │            │
│  │  - Health monitoring                        │            │
│  │  - Tool aggregation (global + agent-scoped) │            │
│  └─────────────────────────────────────────────┘            │
└──────────────────┬───────────────────┬────────────────────┘
                   │                   │
        ┌──────────▼─────────┐ ┌──────▼──────────┐
        │   Ollama Instance   │ │  MCP Servers    │
        │   - Agent A Model   │ │  - Filesystem   │
        │   - Agent B Model   │ │  - Search       │
        │   (可能是相同或不同)  │ │  - Custom Tools │
        └─────────────────────┘ └─────────────────┘
```

## Core Components

### 1. Configuration Layer (`app/schemas/config.py`, `app/services/config_manager.py`)

**Purpose**: Manage all application configuration through declarative YAML files.

**Key Features**:
- **Pydantic Models**: Strong typing and validation for all configuration
- **Environment Variable Substitution**: Secure handling of secrets via `${VAR_NAME}` syntax
- **Validation**: Runtime checks for agent existence, URL formats, model names
- **Import/Export**: Round-trip YAML serialization

**Configuration Structure**:
```yaml
version: "1.0"
conversation:
  starting_agent: "agent_a"
  max_cycles: 10
  turn_timeout: 300
agents:
  agent_a:
    name: "Agent A"
    persona: "System prompt..."
    model:
      url: "http://localhost:11434"
      model_name: "llama2"
      thinking: true
    mcp_servers: ["filesystem"]
  agent_b: ...
mcp_servers:
  global_servers:
    - name: "filesystem"
      command: "mcp-server-filesystem"
      args: ["/tmp"]
initialization:
  first_message: "Hello..."
logging:
  level: "INFO"
```

### 2. Orchestration Layer (`app/core/orchestrator.py`)

**Purpose**: Coordinate turn-taking between agents using LangGraph.

**Architecture**:
- **LangGraph StateGraph**: Manages conversation flow
- **Agent Nodes**: Isolated execution contexts for each agent
- **Tool Node**: Centralized tool execution with routing
- **Cycle Manager**: Tracks conversation progress and termination
- **MemorySaver Checkpointer**: Persistent state for pause/resume

**Graph Structure**:
```
START
  │
  ▼
[Initialization] ─── System prompts + first message
  │
  ▼
[Agent A Node] ◄─────────┐
  │                      │
  │ ┌─ Has tool calls? ──┤
  │ │                    │
  │ ▼                    │
  │ [Tool Node] ─────────┘
  │
  ▼
[Cycle Check] ─── Max cycles? Keywords? Silence?
  │
  ├─ Continue ─────────┐
  │                    │
  ▼                    │
[Agent B Node] ◄───────┤
  │                    │
  │ ┌─ Has tool calls? ─┤
  │ │                   │
  │ ▼                   │
  │ [Tool Node] ────────┘
  │
  ▼
[Cycle Check]
  │
  ├─ Continue ──────────┘
  │
  ▼
 END
```

### 3. Agent Execution (`app/agents/agent_node.py`)

**Purpose**: Execute individual agent turns with persona, tools, and timeout handling.

**Agent Node Workflow**:
1. **Context Preparation**: Inject system prompt with persona
2. **Message History**: Load conversation history from state
3. **LLM Invocation**: Call Ollama with bound tools
4. **Thought Suppression**: Route internal reasoning to agent console (if enabled)
5. **Response Sanitization**: Filter thought artifacts from final message
6. **Timeout Handling**: Enforce turn_timeout with graceful error recovery
7. **State Update**: Append agent response to conversation state

**Thought Suppression**:
When `thinking: true` in agent config:
- Internal reasoning streamed to WebSocket → Agent console (left/right)
- Final response sanitized → Center conversation column
- Preserves transparency without cluttering dialogue

### 4. MCP Integration (`app/services/mcp_manager.py`, `app/services/tool_adapter.py`)

**Purpose**: Provide agents with external capabilities through Model Context Protocol.

**MCP Server Lifecycle**:
1. **Startup**: Launch subprocess with configured command/args
2. **Initialization**: Send MCP initialize request
3. **Health Monitoring**: Periodic checks via list_tools
4. **Tool Discovery**: Enumerate available tools
5. **Execution**: Route tool calls to appropriate server
6. **Shutdown**: Graceful SIGTERM with cleanup

**Tool Aggregation**:
- **Global Servers**: Available to all agents (e.g., filesystem, search)
- **Agent-Scoped Servers**: Private to specific agents (e.g., database access)
- **LangChain Adapter**: Convert MCP tools to LangChain `BaseTool` format

### 5. State Management (`app/core/state.py`)

**Purpose**: Maintain conversation history and control flow state.

**ConversationState Schema**:
```python
{
  "messages": [
    {
      "content": "Hello",
      "agent_id": "agent_a",
      "timestamp": "2024-01-01T12:00:00",
      "is_thought": false,
      "message_type": "ai",
      "metadata": {}
    },
    ...
  ],
  "current_cycle": 3,
  "next_agent": "agent_b",
  "should_terminate": false,
  "termination_reason": null,
  "metadata": {}
}
```

**Message Types**:
- `human`: User input or initial message
- `ai`: Agent response
- `system`: System prompts or notifications
- `tool`: Tool execution results
- `cycle_marker`: Cycle boundary indicators

### 6. Cycle Detection & Termination (`app/core/cycle_manager.py`)

**Purpose**: Determine when conversations should end.

**Cycle Definition**:
- One cycle = All agents have spoken at least once
- Tracks `agents_spoken_this_cycle` set
- Increments `cycles_completed` when cycle finishes

**Termination Conditions**:
1. **Max Cycles**: Hard limit (e.g., 10 cycles)
2. **Keyword Triggers**: Case-insensitive matching (e.g., "goodbye", "exit")
3. **Silence Detection**: N cycles without substantive content (>20 chars)
4. **Manual Stop**: User-initiated via API

### 7. WebSocket Communication (`app/core/websocket_manager.py`)

**Purpose**: Real-time streaming of thoughts, responses, and status updates.

**Connection Manager**:
- **Lifecycle**: connect() → message exchange → disconnect()
- **Message Routing**: send_personal_message(), broadcast()
- **Heartbeat**: Ping/pong to detect disconnections
- **Auto-Reconnection**: Client-side exponential backoff

**Message Types**:
```javascript
{
  type: "thought",  // Agent internal reasoning
  type: "message",  // Agent response
  type: "tool_call", // Tool execution
  type: "cycle_update", // Cycle progression
  type: "conversation_status", // Running/paused/ended
  type: "error"  // Error notifications
}
```

### 8. Error Handling (`app/core/exceptions.py`)

**Custom Exception Hierarchy**:
```
AIAgentMixerException (base)
├── ConfigurationError
│   ├── InvalidConfigError
│   └── ConfigFileNotFoundError
├── OllamaConnectionError
│   ├── OllamaModelNotFoundError
│   └── OllamaTimeoutError
├── MCPServerError
│   ├── MCPStartupError
│   ├── MCPConnectionError
│   └── MCPToolExecutionError
├── AgentExecutionError
│   └── AgentTimeoutError
├── ConversationStateError
├── WebSocketError
└── ValidationError
```

**Global Exception Handlers**:
- Convert exceptions to appropriate HTTP status codes
- Include error details in JSON response
- Log errors with structured context
- Preserve stack traces in logs

### 9. Observability (`app/main.py` metrics)

**Metrics Endpoint** (`/metrics`):
Prometheus-compatible metrics:
- `requests_total`: HTTP request counter
- `requests_errors`: HTTP error counter
- `conversations_started`: Conversation start counter
- `conversations_completed`: Conversation completion counter
- `websocket_connections_active`: Active WebSocket gauge
- `mcp_servers_healthy`: Healthy server count
- `conversation_running`: Boolean gauge

**Logging**:
- Structured JSON logs with timestamps
- Request IDs for tracing
- Agent action logging (turn start/end with timing)
- MCP tool call logging (name, args, result, duration)
- Configuration change logging

## Data Flow

### Starting a Conversation

1. **User uploads YAML** → `/api/config/upload`
2. **Config validation** → Pydantic models
3. **Global MCP servers start** → MCPManager
4. **User clicks "Start"** → `/api/conversation/start`
5. **Orchestrator created** → Load config, build graph
6. **Agent-scoped MCP servers start** (if any)
7. **Initialize state** → System prompts + first message
8. **Graph execution begins** → START node
9. **Cycle loop**:
   - Agent A turn → Ollama call → Response
   - Tool calls (if any) → MCP execution → Results
   - Agent B turn → Ollama call → Response
   - Cycle check → Continue or terminate?
10. **Conversation ends** → Termination reason logged
11. **Final state saved** → Checkpointer

### Real-Time Streaming

1. **Agent invokes LLM** → OllamaClient.generate_response()
2. **Thinking tokens** (if enabled):
   - → ThoughtSuppressingCallback
   - → WebSocketManager.send_to_agent_console()
   - → React AgentConsole component
3. **Final response tokens**:
   - → ConversationLoggingCallback
   - → WebSocketManager.broadcast()
   - → React ConversationExchange component

## Deployment Architecture

### Docker Compose Services

1. **Backend** (FastAPI)
   - Multi-stage build (builder + runtime)
   - Python 3.11-slim base
   - Non-root user (appuser)
   - Health check on `/health`
   - Volumes: config (read-only), logs

2. **Frontend** (Nginx)
   - Multi-stage build (Node.js builder + Nginx)
   - Serves static React build
   - Reverse proxy for `/api` and `/ws`
   - Gzip compression
   - Security headers

3. **Redis** (Optional)
   - State persistence across restarts
   - WebSocket connection state sharing (horizontal scaling)

4. **Ollama** (Optional)
   - Local LLM hosting
   - GPU acceleration support

### Health Checks

- Backend: `curl http://localhost:8000/health`
- Frontend: `curl http://localhost:80/`
- Redis: `redis-cli ping`
- Service dependencies: `depends_on: {condition: service_healthy}`

## Scalability Considerations

### Current Limitations
- Single backend instance (no horizontal scaling yet)
- In-memory state (lost on restart unless Redis configured)
- One conversation at a time per backend instance

### Future Enhancements
- Redis-backed checkpointer for multi-instance state sharing
- Celery/RabbitMQ for async conversation processing
- Conversation queue for handling multiple concurrent requests
- Agent pooling for improved throughput

## Security

### Authentication & Authorization
- **Current**: No authentication (development mode)
- **Recommended**: Add JWT tokens, OAuth2, or API keys

### Configuration Security
- Environment variable substitution for secrets
- No hardcoded credentials
- Read-only config volume mounts in Docker

### Network Security
- CORS configured for trusted origins
- WebSocket origin validation
- Nginx security headers (X-Frame-Options, X-Content-Type-Options)

### Process Security
- Non-root Docker user
- Minimal base images (alpine, slim)
- MCP servers run as subprocesses (isolated)

## Testing Strategy

### Unit Tests (38 tests)
- Configuration validation
- Environment variable substitution
- MCP server config merging
- YAML round-trip serialization

### Integration Tests (26 tests)
- Cycle management
- Turn alternation
- Termination conditions
- Tool invocation
- State management

### E2E Tests
- WebSocket streaming
- Configuration import/export
- Conversation lifecycle
- Error handling

## Monitoring & Debugging

### Logs
- `backend/logs/` - Application logs
- Structured JSON format
- Searchable by request ID, agent ID, conversation ID

### Metrics
- `/metrics` endpoint for Prometheus scraping
- Grafana dashboards for visualization

### Debugging
- LangGraph checkpoints for state inspection
- Agent console for thought streaming
- Tool call logging for MCP debugging

## Performance Characteristics

### Latency
- WebSocket streaming: <100ms
- Agent turn: 2-10s (depends on Ollama model)
- Tool calls: 10-500ms (depends on tool)

### Throughput
- Supports 100+ cycle conversations
- Handles 10+ concurrent WebSocket connections
- Processes 5-10 agent turns per minute

### Resource Usage
- Backend: ~200MB RAM baseline
- Frontend: ~50MB RAM (Nginx)
- Ollama: 2-8GB RAM (model dependent)
- MCP servers: 50-200MB each
