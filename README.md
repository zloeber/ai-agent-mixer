# Synthetic AI Conversation Orchestrator 

## Technical Summary & Purpose

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