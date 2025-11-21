# AI Agent Mixer - Synthetic AI Conversation Orchestrator 

[![Phase 1](https://img.shields.io/badge/Phase%201-Complete-brightgreen.svg)](docs/PHASE1_COMPLETE.md)
[![Phase 2](https://img.shields.io/badge/Phase%202-Complete-brightgreen.svg)](PHASE2_SUMMARY.md)
[![Backend](https://img.shields.io/badge/Backend-FastAPI-009688.svg)](backend/)
[![Frontend](https://img.shields.io/badge/Frontend-React%2BTypeScript-61DAFB.svg)](frontend/)
[![Tests](https://img.shields.io/badge/Tests-91%20passing-brightgreen.svg)](backend/tests/)

A web-based platform for designing, executing, and monitoring structured conversations between configurable AI agents. Built on LangGraph and Ollama, it enables multi-agent interaction experiments, persona testing, and tool integration validation through declarative YAML configuration.

## ✨ Key Features

- 🤖 **Multi-Agent Orchestration**: Structured turn-taking with configurable termination conditions
- 🎭 **Dynamic Personas**: Custom system prompts and behavioral constraints per agent
- 🔧 **MCP Tool Integration**: Global and agent-scoped external capabilities via Model Context Protocol
- 💭 **Thought Isolation**: Separate internal reasoning from external responses
- 📊 **Real-Time Observability**: WebSocket streaming of thoughts, responses, and execution telemetry
- 📝 **YAML Configuration**: Version-controlled, declarative conversation definitions
- 🐳 **Docker Ready**: Production containerization with health checks and monitoring
- 📈 **Prometheus Metrics**: Built-in observability for monitoring and alerting

## 🚀 Quick Start (5 minutes)

### Prerequisites

- **Python 3.11+** (for backend)
- **Node.js 18+** (for frontend)
- **Ollama** running locally or remotely ([Install Ollama](https://ollama.ai/download))
- Ollama models pulled: `ollama pull llama2` and `ollama pull mistral`

### Option 1: Local Development

```bash
# 1. Clone repository
git clone https://github.com/zloeber/ai-agent-mixer.git
cd ai-agent-mixer

# 2. Start backend
cd backend
pip install -e ".[dev]"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 3. Start frontend (new terminal)
cd ../frontend
npm install
npm run dev

# 4. Open browser
# Frontend: http://localhost:5173
# API Docs: http://localhost:8000/docs
```

### Option 2: Docker Compose

```bash
# 1. Set environment variables (if using MCP tools)
export BRAVE_API_KEY="your-api-key"  # Optional

# 2. Start all services
docker-compose up --build

# 3. Open browser
# Frontend: http://localhost:3000
# Backend: http://localhost:8000
```

## 📖 First Conversation

1. **Load Example Configuration**
   - Click "Import Config" in the UI
   - Select `config/example-simple.yaml`
   - Or upload via API: `curl -F "file=@config/example-simple.yaml" http://localhost:8000/api/config/upload`

2. **Verify Configuration**
   - Check "Configuration" panel shows 2 agents
   - Verify Ollama connections: Green indicators for both agents

3. **Start Conversation**
   - Click "Start Conversation"
   - Watch real-time messages in center panel
   - Monitor agent thoughts in left/right consoles (if `thinking: true`)

4. **Export Results**
   - Click "Export Conversation" to save as Markdown
   - View metrics at `http://localhost:8000/metrics`

## 📚 Documentation

- **[Architecture Overview](docs/architecture.md)** - System design, components, and data flow
- **[Configuration Guide](docs/configuration-guide.md)** - Complete YAML reference with examples
- **[API Reference](docs/api.md)** - REST and WebSocket endpoint documentation
- **[Development Guides](docs/)** - Phase summaries and implementation details

## 🎯 Example Configurations

### Simple Two-Agent Conversation
```yaml
# config/example-simple.yaml
version: "1.0"
conversation:
  starting_agent: "agent_a"
  max_cycles: 5
agents:
  agent_a:
    name: "Agent A"
    persona: "You are friendly and curious."
    model:
      url: "http://localhost:11434"
      model_name: "llama2"
  agent_b:
    name: "Agent B"
    persona: "You are knowledgeable and patient."
    model:
      url: "http://localhost:11434"
      model_name: "llama2"
initialization:
  first_message: "Hello! Let's discuss artificial intelligence."
```

More examples in `config/` directory:
- `philosophy-debate.yaml` - Socratic dialogue between philosophers
- `tool-using-agents.yaml` - Research agents with MCP tools
- `example-with-mcp-placeholder.yaml` - Full MCP integration example

## 🛠️ Development

### Running Tests

```bash
cd backend
pytest tests/ -v                      # Run all tests (91 tests)
pytest tests/test_config_manager.py   # Config tests (38 tests)
pytest tests/test_conversation_flow.py # Integration tests (26 tests)
pytest --cov=app --cov-report=term   # With coverage
```

### Code Quality

```bash
# Linting
ruff check app/
black app/ --check

# Type checking
mypy app/
```

### Building Docker Images

```bash
# Backend
docker build -t ai-agent-mixer-backend:latest ./backend

# Frontend
docker build -t ai-agent-mixer-frontend:latest ./frontend
```

## Project Overview

**Synthetic AI Conversation Orchestrator** is a web-based platform for designing, executing, and monitoring structured conversations between two configurable AI agents. Built on LangGraph and Ollama, it enables developers and researchers to simulate multi-agent interactions, test persona behaviors, and validate tool integrations through a unified YAML-driven configuration system.

---

## Core Purpose

### Problem Statement
Modern AI development lacks a standardized environment for orchestrating and observing synthetic conversations between autonomous agents. Testing agent behaviors, comparing model performance, and validating tool-use patterns requires manual scripting and ad-hoc monitoring, making reproducible experiments and systematic debugging impractical.

### Solution
Provide a turnkey platform that transforms conversation design into declarative configuration, enabling:
- **Rapid Prototyping**: Launch complex agent interactions with a single YAML file
- **Observable Execution**: Real-time visibility into internal reasoning vs. external responses
- **Reproducible Research**: Version-controlled conversation definitions with deterministic execution
- **Tool Integration**: Seamless MCP server support for both global and agent-scoped tools

---

## Technical Architecture

### Platform Stack
- **Backend**: FastAPI + Python 3.11 orchestrating LangGraph state machines
- **Agent Framework**: LangGraph for conversation flow management, LangChain for LLM abstraction
- **LLM Integration**: Ollama with dynamic endpoint configuration per agent
- **Tool Protocol**: Model Context Protocol (MCP) for standardized tool access
- **Frontend**: React 18 + TypeScript + WebSockets for real-time streaming
- **Configuration**: Pydantic-validated YAML with environment variable substitution

### Key Design Principles
1. **Separation of Concerns**: Agent logic, orchestration, and presentation are independently testable
2. **State-Driven**: LangGraph checkpoint system ensures conversation state is always recoverable
3. **Streaming-First**: Real-time token streaming for both thoughts and responses minimizes latency
4. **Configuration as Code**: Entire conversation topology is exportable as a single YAML artifact

---

## Primary Capabilities

### Multi-Agent Orchestration
- **Turn-Based Conversations**: Strict cycle counting with configurable termination conditions
- **Dynamic Personas**: Per-agent system prompts and behavioral constraints
- **Model Flexibility**: Each agent connects to independent Ollama instances/models
- **Starting Agent Control**: Explicit configuration of which agent initiates interaction

### Thought Isolation & Observability
- **Dual-Channel Output**: Thinking models stream internal reasoning to dedicated agent consoles
- **Sanitized Responses**: Final agent responses exclude thought artifacts before transmission
- **Three-Column Interface**: Real-time separation of Agent A console, conversation exchange, and Agent B console
- **Execution Telemetry**: Comprehensive logging of tool calls, cycle timing, and token usage

### MCP Server Management
- **Global Tool Registry**: MCP servers available to all agents (e.g., filesystem, search)
- **Agent-Scoped Tools**: Private MCP server instances for individual agent capabilities
- **Lifecycle Automation**: Automatic startup, health monitoring, and graceful shutdown
- **Configuration Merging**: Agent tools extend global toolset without conflict

### YAML-Driven Configuration
- **Single-File Definition**: Export/import entire conversation topology including agents, models, MCP servers, and termination logic
- **Version Migration**: Schema versioning with backward compatibility
- **Validation**: Runtime Pydantic validation with IDE-friendly JSON schema
- **Parameterization**: Environment variable substitution for secrets and endpoints

---

## Target Use Cases

1. **Agent Behavior Research**: Study emergent behaviors in synthetic social interactions
2. **Model Comparison**: A/B test different LLMs on identical conversation scenarios
3. **Tool Integration Testing**: Validate MCP server functionality in multi-agent contexts
4. **Persona Development**: Iterate on agent personalities and system prompts
5. **Educational Simulations**: Create Socratic dialogues or expert consultations
6. **AI Safety Testing**: Observe agent interactions in controlled, reproducible environments

---

## Success Metrics

- **Latency**: <100ms WebSocket streaming latency for thoughts
- **Throughput**: Support 100+ cycle conversations without memory degradation
- **Reliability**: 99.9% conversation completion rate under normal conditions
- **Flexibility**: Zero-code deployment of new conversation types via YAML
- **Observability**: Complete conversation traceability from configuration to execution

---

## Development Status

This platform is designed for production use in research and development environments, providing a foundational layer for:
- Multi-agent system experimentation
- LLM benchmarking frameworks
- Tool-use validation pipelines
- Conversational AI safety research

The architecture supports horizontal scaling via Redis-backed state management and is extensible to multi-agent scenarios beyond the initial two-agent design.

---

## Current Implementation Status

### ✅ Phase 1: Foundation & Core Infrastructure (COMPLETE)

All Phase 1 features have been successfully implemented:

1. **Project Structure & Dependency Setup**
   - Monorepo structure with backend (Python/FastAPI) and frontend (React/TypeScript)
   - All dependencies installed and tested
   - Docker support with docker-compose.yml

2. **Configuration Schema & Pydantic Models**
   - Complete Pydantic models for all configuration types
   - JSON schema generation for IDE support
   - Comprehensive validation

3. **YAML Import/Export Service**
   - Load/save configuration from YAML files
   - Environment variable substitution
   - Configuration validation with detailed errors

4. **Basic FastAPI Application Skeleton**
   - Health check and configuration endpoints
   - CORS middleware for frontend
   - JSON structured logging
   - Global exception handling

5. **React Three-Column Layout Shell**
   - Responsive three-column layout (Agent A | Conversation | Agent B)
   - Dark theme with TailwindCSS
   - Shell components for all major UI sections

6. **WebSocket Manager & Connection Handler**
   - Backend WebSocket manager with connection pooling
   - Frontend WebSocket service with auto-reconnection
   - Heartbeat/ping-pong for connection monitoring

See [Phase 1 Complete Documentation](docs/PHASE1_COMPLETE.md) for detailed information.

### ✅ Phase 2: Agent Engine & LangGraph Integration (COMPLETE)

All Phase 2 features have been successfully implemented:

1. **Ollama Integration Layer**
   - OllamaClient service with connection verification
   - Streaming and non-streaming response generation
   - Model availability checking
   - Connection testing API endpoint

2. **Thought Suppression Callback Mechanism**
   - ThoughtSuppressingCallback for separating internal reasoning
   - Real-time thought streaming to agent consoles
   - Multiple thought pattern detection (XML, markdown, etc.)
   - ConversationLoggingCallback for telemetry

3. **LangGraph State Definition**
   - AgentMessage model with metadata
   - ConversationState TypedDict
   - ConversationStateManager for state operations
   - Serialization and persistence support

4. **Agent Node Factory**
   - create_agent_node() for LangGraph-compatible nodes
   - Persona injection and timeout handling
   - Streaming and non-streaming variants
   - Comprehensive error handling

5. **Conversation Orchestrator Graph**
   - ConversationOrchestrator with LangGraph workflow
   - Dynamic agent node creation
   - Cycle check and routing logic
   - State persistence with checkpointing

6. **Cycle Detection & Termination Logic**
   - CycleManager for tracking conversation cycles
   - Max cycles termination
   - Keyword trigger detection
   - Silence detection

7. **Initialization & First Message Handling**
   - PromptBuilder with Jinja2 template rendering
   - ConversationInitializer for state setup
   - System prompt construction
   - Configuration validation

See [Phase 2 Summary](PHASE2_SUMMARY.md) for detailed information.

### 🚧 Coming Next: Phase 3 - MCP Server Integration

- MCP Server Manager
- Global MCP configuration
- Per-agent MCP server scoping
- Tool routing and execution

## Installation

### Prerequisites

- Python 3.11+
- Node.js 18+
- uv (Python package manager)
- Ollama (for running LLM models)

### Backend Setup

```bash
cd backend
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e .

# Copy and configure environment
cp .env.template .env
# Edit .env with your settings

# Run backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup

```bash
cd frontend
npm install

# Copy and configure environment
cp .env.template .env
# Edit .env with your settings

# Run frontend dev server
npm run dev

# Build for production
npm run build
```

### Docker Setup

```bash
# Build and start all services
docker-compose up --build

# Access the application
# Frontend: http://localhost:3000
# Backend: http://localhost:8000
```

## Configuration

### Sample Configuration

A sample configuration is provided at `config/example-simple.yaml`:

```yaml
version: "1.0"
conversation:
  starting_agent: "agent_a"
  max_cycles: 5
  turn_timeout: 120

agents:
  agent_a:
    name: "Agent A"
    persona: "You are a friendly AI assistant"
    model:
      provider: "ollama"
      url: "http://localhost:11434"
      model_name: "llama2"
      
  agent_b:
    name: "Agent B"
    persona: "You are a knowledgeable AI assistant"
    model:
      provider: "ollama"
      url: "http://localhost:11434"
      model_name: "llama2"

initialization:
  first_message: "Hello! Let's have a conversation."

logging:
  level: "INFO"
```

## API Documentation

### Backend Endpoints

**Configuration Management**:
- `GET /health` - Health check
- `GET /api/config/schema` - Get configuration JSON schema
- `POST /api/config/import` - Import configuration from JSON
- `GET /api/config/export` - Export current configuration
- `POST /api/config/validate` - Validate YAML configuration
- `POST /api/config/upload` - Upload YAML configuration file

**Ollama Management**:
- `POST /api/ollama/test-connection` - Test Ollama connection and model availability

**Conversation Control**:
- `POST /api/conversation/start` - Start a new conversation
- `POST /api/conversation/stop` - Stop the current conversation
- `GET /api/conversation/status` - Get conversation status

**WebSocket**:
- `GET /api/ws/status` - WebSocket connection status
- `WS /ws/{client_id}` - WebSocket endpoint for real-time updates

### Testing

```bash
# Backend
cd backend
source .venv/bin/activate
pytest

# Frontend
cd frontend
npm test

# End-to-end tests
npm run test:e2e
```

## Development

### Project Structure

```
ai-agent-mixer/
├── backend/           # FastAPI backend
│   ├── app/
│   │   ├── schemas/   # Pydantic models
│   │   ├── services/  # Business logic
│   │   ├── core/      # Core infrastructure
│   │   └── agents/    # Agent implementations
│   └── tests/
├── frontend/          # React frontend
│   ├── src/
│   │   ├── components/
│   │   └── services/
│   └── public/
├── config/            # Configuration files
├── docs/              # Documentation
└── tests/             # Integration tests
```

### Contributing

This project is developed following the specifications in `PROJECT_SPECS.md`. Each phase builds upon the previous one:

1. Phase 1: Foundation & Core Infrastructure (✅ Complete)
2. Phase 2: Agent Engine & LangGraph Integration (✅ Complete)
3. Phase 3: MCP Server Integration (🚧 Next)
4. Phase 4: Web Interface & Real-Time Features
5. Phase 5: Testing, Polish & Deployment

## License

See LICENSE file for details.

## Support

For questions or issues:
- Review the [Phase 1 Documentation](docs/PHASE1_COMPLETE.md)
- Check [PROJECT_SPECS.md](PROJECT_SPECS.md) for detailed specifications
- Open an issue on GitHub