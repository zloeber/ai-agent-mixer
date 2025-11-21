# Synthetic AI Conversation Orchestrator - Sequential Feature Specifications

This document provides a step-by-step breakdown of developer specifications that can be used as AI agent prompts to build the complete application. Each feature is atomic, actionable, and builds upon previous work.

---

## Phase 1: Foundation & Core Infrastructure

### Feature 1.1: Project Structure & Dependency Setup
**Description**: Initialize the monorepo structure and install all required dependencies for both backend and frontend.

**Technical Requirements**:
- Create directory structure: `/backend`, `/frontend`, `/config`, `/tests`, `/docs`
- Initialize Python project with uv: `pyproject.toml` with FastAPI, LangGraph, Pydantic, PyYAML, `langchain-ollama`, `mcp` SDK
- Initialize React TypeScript project with Vite: `package.json` with React 18, TypeScript, TailwindCSS, WebSocket client, Monaco Editor
- Create `.env.template` files for both environments
- Add `docker-compose.yml` skeleton

**Acceptance Criteria**:
- `uv install` completes without errors
- `npm install` completes without errors
- Both backends and frontend can start without crashing
- All dependencies are at compatible versions

---

### Feature 1.2: Configuration Schema & Pydantic Models
**Description**: Define the complete YAML configuration schema using Pydantic models for runtime validation and type safety.

**Technical Requirements**:
- Create `/backend/app/schemas/config.py` with Pydantic models:
  - `ModelConfig` (provider, url, model_name, parameters, thinking boolean)
  - `MCPServerConfig` (name, command, args, env dict)
  - `AgentConfig` (name, persona, model, mcp_servers list)
  - `ConversationConfig` (starting_agent, max_cycles, turn_timeout, termination_conditions)
  - `LoggingConfig` (level, include_thoughts, output_directory)
  - `RootConfig` (version, metadata, conversation, agents dict, mcp_servers global, initialization, logging)
- Add JSON schema generation endpoint
- Include validation for Ollama URL formats and model name patterns

**Acceptance Criteria**:
- Pydantic models validate all fields from example YAML
- Invalid configurations raise clear, specific errors
- JSON schema can be exported and used for IDE autocomplete

---

### Feature 1.3: YAML Import/Export Service
**Description**: Build service for loading and saving complete configuration from/to YAML files.

**Technical Requirements**:
- Create `/backend/app/services/config_manager.py`:
  - `load_config(filepath: str) -> RootConfig`
  - `save_config(config: RootConfig, filepath: str)`
  - `validate_config_yaml(yaml_content: str) -> Tuple[bool, List[str]]`
- Handle environment variable substitution (e.g., `${BRAVE_API_KEY}`)
- Support configuration merging (global + agent-specific MCP servers)
- Add file watcher for hot-reloading (optional)

**Acceptance Criteria**:
- Can load and parse example YAML configuration without errors
- Exporting imported config produces semantically identical YAML
- Environment variables are correctly substituted
- Validation errors return specific line numbers and messages

---

### Feature 1.4: Basic FastAPI Application Skeleton
**Description**: Create the foundational FastAPI application with CORS, error handling, and health checks.

**Technical Requirements**:
- Create `/backend/app/main.py`:
  - FastAPI app with lifespan context manager
  - CORS middleware configured for frontend origin
  - Global exception handlers for validation errors
  - Health check endpoint `/health` returning 200
  - Configuration endpoints: `POST /api/config/import`, `GET /api/config/export`, `POST /api/config/validate`
- Create `/backend/app/core/logging.py` with JSON formatted logs
- Add startup/shutdown events for resource cleanup

**Acceptance Criteria**:
- API starts on port 8000 and responds to `/health`
- Configuration endpoints accept/return correct data structures
- CORS allows requests from localhost:3000
- Graceful shutdown handles SIGTERM

---

### Feature 1.5: React Three-Column Layout Shell
**Description**: Build the basic responsive three-column UI layout without functionality.

**Technical Requirements**:
- Create `/frontend/src/App.tsx` with grid layout:
  - Left column: Agent A console (25% width)
  - Center column: Conversation exchange (50% width)
  - Right column: Agent B console (25% width)
- Create shell components:
  - `AgentConsole.tsx` (accepts `agentId` prop)
  - `ConversationExchange.tsx`
  - `ConfigurationPanel.tsx` (collapsible sidebar)
- Use TailwindCSS for styling with proper flexbox/grid
- Implement responsive behavior: stacks vertically on mobile
- Add basic header with app title and status indicator

**Acceptance Criteria**:
- Layout renders correctly at 1920x1080, 1366x768, and mobile breakpoints
- Three columns are visually distinct with borders/backgrounds
- All three shell components mount without errors
- UI scales properly when window is resized

---

### Feature 1.6: WebSocket Manager & Connection Handler
**Description**: Implement WebSocket infrastructure for real-time streaming between backend and frontend.

**Technical Requirements**:
- Backend: Create `/backend/app/core/websocket_manager.py`:
  - `ConnectionManager` class with `active_connections: Dict[str, WebSocket]`
  - Methods: `connect`, `disconnect`, `send_personal_message`, `broadcast`
  - Endpoint: `/ws/{client_id}` for WebSocket connections
- Frontend: Create `/frontend/src/services/websocketService.ts`:
  - Singleton WebSocket manager
  - Auto-reconnection logic with exponential backoff
  - Event emitter pattern for component subscriptions
- Implement heartbeat/ping-pong to detect disconnections

**Acceptance Criteria**:
- WebSocket connection establishes successfully from frontend
- Can send and receive JSON messages in both directions
- Connection recovers automatically after server restart
- No memory leaks when connections are opened/closed repeatedly

---

## Phase 2: Agent Engine & LangGraph Integration

### Feature 2.1: Ollama Integration Layer
**Description**: Build service for connecting to configurable Ollama instances with dynamic URL/model support.

**Technical Requirements**:
- Create `/backend/app/services/ollama_client.py`:
  - `OllamaClient` class that accepts `ModelConfig`
  - Methods: `generate_response(messages: List[Message]) -> Message`, `verify_connection() -> bool`
  - Support streaming responses with callbacks
  - Handle connection errors, timeouts, and model not found errors
  - Implement connection pooling for performance
- Add endpoint: `POST /api/ollama/test-connection` to verify settings

**Acceptance Criteria**:
- Can successfully connect to Ollama at configurable URL (localhost and remote)
- Can load and use different models (llama2, mistral, etc.)
- Streaming responses emit tokens in real-time
- Proper error messages for unreachable servers or invalid models

---

### Feature 2.2: Thought Suppression Callback Mechanism
**Description**: Implement callback handler that captures model thinking and routes it separately from final responses.

**Technical Requirements**:
- Create `/backend/app/core/callbacks.py`:
  - `ThoughtSuppressingCallback(BaseCallbackHandler)` class
  - Track `is_thinking` state based on prompt prefixes
  - Route thought tokens to agent-specific console via WebSocket
  - Filter out thought patterns from final response (e.g., "I think...", "Let me consider...")
- Support multiple thinking formats: XML tags, markdown blocks, custom delimiters

**Acceptance Criteria**:
- When `thinking: true` in config, internal reasoning appears in agent console only
- When `thinking: false`, no extra content appears in either console or conversation
- Thoughts are streamed in real-time, not batched
- Final response to other agent contains no thought artifacts

---

### Feature 2.3: LangGraph State Definition
**Description**: Define the conversation state structure and message types for LangGraph.

**Technical Requirements**:
- Create `/backend/app/core/state.py`:
  - `AgentMessage` pydantic model (extends LangChain's BaseMessage with `agent_id`, `timestamp`, `is_thought`)
  - `ConversationState` TypedDict with `messages: List[AgentMessage]`, `current_cycle: int`, `next_agent: str`
  - `ConfigSchema` for graph configuration
- Add serialization/deserialization methods for state persistence
- Define message types: `HumanMessage`, `AIMessage`, `ToolMessage`, `CycleMarkerMessage`

**Acceptance Criteria**:
- State can be serialized to JSON and persisted to disk
- All message types are distinguishable and properly typed
- State can be loaded back without losing information
- Compatible with LangGraph's checkpointing system

---

### Feature 2.4: Agent Node Factory
**Description**: Create factory function that generates LangGraph nodes for each agent with full configuration.

**Technical Requirements**:
- Create `/backend/app/agents/agent_node.py`:
  - `create_agent_node(agent_id: str, agent_config: AgentConfig)` function
  - Node handles: persona prompt injection, tool binding, model invocation
  - Integrate thought suppression callback
  - Implement timeout handling (respects `turn_timeout` from config)
  - Return message with proper `agent_id` attribution
- Support both streaming and non-streaming modes

**Acceptance Criteria**:
- Factory produces callable node compatible with LangGraph
- Node executes agent turn with correct persona and model settings
- Timeout errors are caught and converted to graceful failure messages
- Generated messages are correctly attributed to the agent

---

### Feature 2.5: Conversation Orchestrator Graph
**Description**: Build the main LangGraph workflow that manages turn-taking between agents.

**Technical Requirements**:
- Create `/backend/app/core/orchestrator.py`:
  - `ConversationOrchestrator` class
  - Initialize `StateGraph` with `ConversationState`
  - Add nodes: `agent_a`, `agent_b`, `tools`, `cycle_check`
  - Add conditional edges: `route_to_next_agent` function
  - Add entry point based on `starting_agent` config
  - Compile graph with `checkpointer` for persistence
- Implement cycle counting logic in `cycle_check` node

**Acceptance Criteria**:
- Graph can be compiled without errors
- Starting agent is correctly set from configuration
- Turn order alternates between agents unless tools are called
- Graph execution can be paused and resumed using checkpoints

---

### Feature 2.6: Cycle Detection & Termination Logic
**Description**: Implement intelligent cycle counting and conversation termination conditions.

**Technical Requirements**:
- Create `/backend/app/core/cycle_manager.py`:
  - `CycleManager` class tracking turn history
  - Detect when "all agents have completed an interaction" (1 cycle)
  - Check `max_cycles` limit
  - Implement `keyword_triggers` detection (scan messages for termination phrases)
  - Implement `silence_detection` (n cycles without new substantive content)
  - Return `should_terminate` flag and reason
- Integrate into LangGraph as conditional edge from `cycle_check` node

**Acceptance Criteria**:
- Cycle count increments correctly after each agent has spoken once
- Conversation stops at exactly `max_cycles`
- Keyword triggers immediately terminate conversation
- Silence detection activates after configured number of cycles
- Termination reason is logged and available to frontend

---

### Feature 2.7: Initialization & First Message Handling
**Description**: Build system prompt construction and injection of the first message to start conversations.

**Technical Requirements**:
- Create `/backend/app/services/prompt_builder.py`:
  - `build_system_prompt(agent_config, global_context, tools)` function
  - Render Jinja2 template from `initialization.system_prompt_template`
  - Inject persona, available tools, and starting instructions
  - Compile final prompt respecting token limits
- Create `/backend/app/services/initializer.py`:
  - Construct initial state with system messages for both agents
  - Add first user message from `initialization.first_message`
  - Set `next_agent` based on `starting_agent` config

**Acceptance Criteria**:
- System prompts include correct persona and tool information
- First message is properly formatted and attributed
- Initial state is valid and ready for graph execution
- Token counts are logged for debugging

---

## Phase 3: MCP Server Integration

### Feature 3.1: MCP Server Manager
**Description**: Build service to launch, monitor, and manage MCP server processes globally.

**Technical Requirements**:
- Create `/backend/app/services/mcp_manager.py`:
  - `MCPManager` singleton class
  - `start_server(config: MCPServerConfig) -> Process` using `subprocess.Popen`
  - Monitor stdout/stderr for errors and readiness signals
  - Health check: send initialize request and verify response
  - `stop_server(name: str)` for graceful shutdown (SIGTERM)
  - `restart_server(name: str)` for failure recovery
  - Store server processes in `active_servers: Dict[str, subprocess.Popen]`

**Acceptance Criteria**:
- Can start filesystem MCP server and successfully initialize
- Process is properly terminated on shutdown with no zombies
- Health check detects failed servers within 5 seconds
- Restart mechanism recovers from crashes
- Logs from MCP servers are captured and available

---

### Feature 3.2: Global MCP Configuration
**Description**: Enable configuration and lifecycle management of globally scoped MCP servers.

**Technical Requirements**:
- Extend `MCPManager` to read `mcp_servers.global` from config
- On startup: iterate global servers and launch each
- On shutdown: gracefully terminate all global servers
- Create endpoint: `GET /api/mcp/status` returning health of all servers
- Implement connection pooling for MCP server communication

**Acceptance Criteria**:
- All globally configured MCP servers start automatically on application startup
- Status endpoint shows running/stopped state for each server
- Agents can communicate with global MCP servers without per-agent config
- Failed global servers trigger warnings but don't crash the app

---

### Feature 3.3: Per-Agent MCP Server Scoping
**Description**: Allow individual agents to have their own MCP server instances in addition to global ones.

**Technical Requirements**:
- Extend agent initialization to launch agent-scoped MCP servers
- Modify `get_tools_for_agent(agent_id)` to aggregate:
  - All global MCP tools
  - Agent-specific MCP tools (if any)
- Prevent naming conflicts: prefix agent-scoped server names with `agent_id_`
- Ensure agent-scoped servers are terminated when agent is destroyed
- Update tool routing in LangGraph to use correct MCP server set per agent

**Acceptance Criteria**:
- Agents can use both global and their own dedicated MCP servers
- Agent A cannot access Agent B's scoped servers
- No port conflicts when running multiple agent-scoped servers
- Configuration correctly merges global and agent-level MCP settings

---

### Feature 3.4: Tool Routing & Execution
**Description**: Integrate MCP tools into LangGraph and route tool calls to correct servers.

**Technical Requirements**:
- Create `/backend/app/services/tool_adapter.py`:
  - Convert MCP tools to LangChain `BaseTool` format
  - Implement `MCPAdapterTool` that forwards calls to MCP server
  - Handle tool arguments and return value serialization
- Update orchestrator graph:
  - Add `ToolNode` with all available tools
  - Conditional edge from agents: if `response.tool_calls` exists, route to `tools` node
  - From `tools` node, route back to original agent
- Implement tool call logging (agent, tool name, args, result, duration)

**Acceptance Criteria**:
- Agents can invoke MCP tools during conversation
- Tool results are correctly returned to the calling agent
- Tool errors are gracefully handled and reported to agent as error message
- Tools from multiple MCP servers (global + agent-scoped) work simultaneously

---

## Phase 4: Web Interface & Real-Time Features

### Feature 4.1: Agent Console WebSocket Streaming
**Description**: Implement real-time streaming of agent thoughts and debug output to left/right console columns.

**Technical Requirements**:
- Backend: In `ThoughtSuppressingCallback`, send thought tokens via WebSocket:
  ```python
  await websocket_manager.send_to_agent_console(
      agent_id, 
      {"type": "thought", "content": token, "timestamp": datetime.utcnow()}
  )
  ```
- Frontend: Update `AgentConsole.tsx`:
  - Subscribe to WebSocket events for specific `agent_id`
  - Maintain scrollable message history in component state
  - Render thoughts with monospace font and subtle styling
  - Auto-scroll to bottom as new messages arrive
  - Add "Clear Console" button

**Acceptance Criteria**:
- Thoughts appear in real-time as agent generates them
- Each agent's console shows only its own thoughts
- Console scrolls automatically during streaming
- Performance: handles 1000+ messages without lag

---

### Feature 4.2: Conversation Exchange Component
**Description**: Build the center column showing the actual agent-to-agent dialogue with turn indicators.

**Technical Requirements**:
- Frontend: Enhance `ConversationExchange.tsx`:
  - Subscribe to "conversation_message" WebSocket events
  - Display messages in alternating bubbles (Agent A left-aligned, Agent B right-aligned)
  - Show agent name, timestamp, and cycle number for each message
  - Add visual indicator for current turn (highlight agent whose turn it is)
  - Implement "Export Conversation" button to download as markdown
  - Add pause/resume conversation controls

**Acceptance Criteria**:
- Messages appear in center column as conversation progresses
- Messages are visually distinct by agent with clear attribution
- Cycle counter updates correctly
- Export produces valid markdown file with full conversation history
- UI updates do not cause console columns to re-render unnecessarily

---

### Feature 4.3: Configuration Editor Panel
**Description**: Build live YAML configuration editor with validation and connection testing.

**Technical Requirements**:
- Frontend: Create `ConfigurationPanel.tsx`:
  - Integrate Monaco Editor with YAML language support
  - Fetch JSON schema from backend for autocomplete
  - "Validate" button that calls `POST /api/config/validate`
  - "Test Ollama Connections" button that tests both agent endpoints
  - "Apply" button to import new configuration
  - Display validation errors inline with line numbers
- Add MCP server health indicators (green/red circles)

**Acceptance Criteria**:
- Editor provides syntax highlighting and autocomplete
- Invalid YAML shows real-time errors
- Connection test button shows success/failure for each agent's Ollama URL
- Applying valid configuration updates the system without restart
- Errors are displayed in user-friendly format with line numbers

---

### Feature 4.4: Conversation Control Dashboard
**Description**: Add start/stop/pause controls and status display to the interface.

**Technical Requirements**:
- Frontend: Create `ControlPanel.tsx`:
  - "Start Conversation" button (enabled only when config is loaded)
  - "Stop" button (terminates current run)
  - "Pause/Resume" toggle
  - Status display: idle / running / paused / terminated
  - Progress indicator: current cycle / max cycles
  - Input field to set max cycles (overrides config)
  - Dropdown to select starting agent (overrides config)
- Backend: Create `/api/conversation/start`, `/stop`, `/pause`, `/resume` endpoints
- Implement conversation state machine in orchestrator

**Acceptance Criteria**:
- All controls function correctly and disable appropriately based on state
- Conversation can be paused mid-cycle and resumed correctly
- Starting a new conversation clears previous state
- Status is synchronized across all connected clients via WebSocket

---

### Feature 4.5: Configuration Import/Export UI
**Description**: Add file-based import/export functionality with drag-and-drop support.

**Technical Requirements**:
- Frontend: Add to `ConfigurationPanel.tsx`:
  - "Import YAML" button with file picker
  - Drag-and-drop zone for YAML files
  - "Export Current Config" button downloads YAML file
  - Display current config name and path
- Backend: Create `/api/config/import-file` endpoint accepting multipart file upload
- Validate imported file before applying
- Save exported files with timestamp in filename

**Acceptance Criteria**:
- Can import configuration via file picker and drag-and-drop
- Invalid YAML files show error without applying changes
- Export downloads a valid YAML file that can be re-imported
- Imported configuration is immediately active

---

## Phase 5: Testing, Polish & Deployment

### Feature 5.1: Unit Tests for Configuration Management
**Description**: Write comprehensive unit tests for YAML parsing and validation logic.

**Technical Requirements**:
- Create `/backend/tests/test_config_manager.py`:
  - Test valid config loading
  - Test invalid config error messages
  - Test environment variable substitution
  - Test config export/import roundtrip
  - Test MCP server config merging (global + agent)
- Use pytest fixtures for sample configurations
- Achieve 90% code coverage

**Acceptance Criteria**:
- All tests pass
- Invalid configs raise specific exceptions
- Tests cover edge cases: missing fields, type mismatches, malformed URLs

---

### Feature 5.2: Integration Tests for Conversation Flow
**Description**: Build E2E tests for the complete conversation lifecycle.

**Technical Requirements**:
- Create `/backend/tests/test_conversation_flow.py`:
  - Mock Ollama responses using `FakeListLLM`
  - Test single cycle execution
  - Test multi-cycle execution up to max_cycles
  - Test termination on keyword trigger
  - Test tool invocation and result handling
  - Test pause/resume functionality
- Use LangGraph's `MemorySaver` checkpointer for test isolation

**Acceptance Criteria**:
- Conversation completes expected number of cycles
- Turn order alternates correctly
- Tool calls are executed and results returned
- Pause stops execution before next agent turn

---

### Feature 5.3: End-to-End Frontend Tests
**Description**: Add Cypress/Playwright tests for critical user journeys.

**Technical Requirements**:
- Create `/frontend/cypress/e2e/` tests:
  - Load sample config and verify three columns render
  - Start conversation and see messages appear
  - Verify thoughts appear in agent consoles but not center
  - Test configuration import/export
  - Test pause/resume buttons
- Mock WebSocket connections for predictable testing
- Test responsive layout on mobile viewport

**Acceptance Criteria**:
- All E2E tests pass in CI pipeline
- Tests cover primary user flows without flakiness
- Can run against local dev server

---

### Feature 5.4: Docker Containerization
**Description**: Create production-ready Docker images and orchestration.

**Technical Requirements**:
- Backend `Dockerfile`: multi-stage build, Python 3.11-slim, install uv dependencies
- Frontend `Dockerfile`: Nginx base, build static files, serve on port 80
- `docker-compose.yml`:
  - orchestrator service with volume mounts for config/logs
  - frontend service
  - optional ollama service
  - redis service for WebSocket scaling
- Create `.dockerignore` files
- Add healthcheck endpoints to all services

**Acceptance Criteria**:
- `docker-compose up` starts all services
- Frontend can connect to backend API
- Configuration files can be edited on host and reloaded
- Containers restart automatically on failure

---

### Feature 5.5: Error Handling & Observability
**Description**: Implement comprehensive error handling, logging, and monitoring.

**Technical Requirements**:
- Backend: Create `/backend/app/core/exceptions.py`:
  - Custom exceptions: `OllamaConnectionError`, `MCPStartupError`, `InvalidConfigError`
  - Global exception handlers return appropriate HTTP status codes
- Add structured logging throughout:
  - Agent turn start/end with timing
  - MCP tool calls with arguments and results
  - Configuration changes with user info
- Create `/metrics` endpoint for Prometheus scraping
- Add request ID tracing across WebSocket and HTTP

**Acceptance Criteria**:
- All errors are caught and return user-friendly messages
- Logs are in JSON format with consistent structure
- Can trace a conversation flow through logs
- Metrics endpoint shows request counts, error rates, and durations

---

### Feature 5.6: Documentation & Examples
**Description**: Write comprehensive documentation and sample configurations.

**Technical Requirements**:
- Create `/docs/architecture.md` explaining system design
- Create `/docs/configuration-guide.md` with YAML reference
- Create `/docs/api.md` with all REST and WebSocket endpoints
- Add `/config/examples/` directory with:
  - `philosophy-debate.yaml`
  - `tool-using-agents.yaml`
  - `debug-thoughts.yaml`
- Add inline code comments and docstrings
- Create README with quick start guide

**Acceptance Criteria**:
- New developer can set up project in < 15 minutes following README
- Example configurations can be imported and run without modification
- All public APIs are documented with request/response examples
- Code has 70% docstring coverage

---

## Implementation Order Summary

1. **Setup**: 1.1 → 1.2 → 1.3 → 1.4
2. **UI Shell**: 1.5 → 1.6
3. **Agent Core**: 2.1 → 2.2 → 2.3 → 2.4
4. **Orchestration**: 2.5 → 2.6 → 2.7
5. **MCP**: 3.1 → 3.2 → 3.3 → 3.4
6. **Real-time UI**: 4.1 → 4.2 → 4.3 → 4.4 → 4.5
7. **Polish**: 5.1 → 5.2 → 5.3 → 5.4 → 5.5 → 5.6

Each feature specification is ready to be used as a standalone AI prompt. For best results, provide one feature at a time to your AI agent and ensure acceptance criteria are met before moving to the next.