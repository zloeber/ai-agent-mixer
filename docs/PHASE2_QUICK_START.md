# Phase 2 Quick Start Guide

This guide helps you quickly understand and use the Phase 2 implementation.

## What Phase 2 Provides

Phase 2 implements the core agent engine that enables AI agents to have conversations using LangGraph orchestration.

### Key Capabilities

1. **Multi-Agent Conversations**: Two or more AI agents can converse with each other
2. **LLM Integration**: Connect to Ollama for running local language models
3. **Thought Suppression**: Separate internal reasoning from external responses
4. **Cycle Management**: Track conversation rounds and terminate based on conditions
5. **State Persistence**: Save and resume conversation state

---

## Quick Example

### 1. Load Configuration

```python
from app.services.config_manager import load_config

config = load_config("config/example-simple.yaml")
```

### 2. Create Orchestrator

```python
from app.core.orchestrator import ConversationOrchestrator

orchestrator = ConversationOrchestrator(config)
```

### 3. Start Conversation

```python
import asyncio

async def run_conversation():
    # Initialize
    metadata = await orchestrator.start_conversation()
    print(f"Started conversation: {metadata['conversation_id']}")
    
    # Run until completion
    final_state = await orchestrator.run_conversation()
    
    # Get results
    print(f"Completed after {final_state['current_cycle']} cycles")
    print(f"Reason: {final_state['termination_reason']}")

asyncio.run(run_conversation())
```

---

## Configuration Example

```yaml
version: "1.0"

conversation:
  starting_agent: "agent_a"
  max_cycles: 5
  turn_timeout: 120
  termination_conditions:
    keyword_triggers: ["goodbye"]
    silence_detection: 3

agents:
  agent_a:
    name: "Socrates"
    persona: "You are Socrates, asking probing questions."
    model:
      provider: "ollama"
      url: "http://localhost:11434"
      model_name: "llama2"
      thinking: true  # Enable thought streaming
      parameters:
        temperature: 0.7

  agent_b:
    name: "Plato"
    persona: "You are Plato, providing thoughtful responses."
    model:
      provider: "ollama"
      url: "http://localhost:11434"
      model_name: "llama2"
      thinking: false

initialization:
  system_prompt_template: |
    You are {{ agent.name }}.
    {{ agent.persona }}
  first_message: "What is the nature of knowledge?"
```

---

## API Usage

### Test Ollama Connection

```bash
curl -X POST http://localhost:8000/api/ollama/test-connection \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "ollama",
    "url": "http://localhost:11434",
    "model_name": "llama2",
    "thinking": false,
    "parameters": {"temperature": 0.7}
  }'
```

### Start Conversation

```bash
# 1. Upload configuration
curl -X POST http://localhost:8000/api/config/upload \
  -F "file=@config/example-simple.yaml"

# 2. Start conversation
curl -X POST http://localhost:8000/api/conversation/start

# 3. Check status
curl http://localhost:8000/api/conversation/status
```

---

## WebSocket Events

Connect to `ws://localhost:8000/ws/{client_id}` to receive real-time events:

### Conversation Started
```json
{
  "type": "conversation_started",
  "conversation_id": "uuid",
  "max_cycles": 5,
  "agents": ["agent_a", "agent_b"]
}
```

### Thought Stream (when thinking enabled)
```json
{
  "type": "thought",
  "agent_id": "agent_a",
  "content": "Let me consider this question...",
  "timestamp": "2024-01-01T00:00:00"
}
```

### Conversation Message
```json
{
  "type": "conversation_message",
  "agent_id": "agent_a",
  "agent_name": "Socrates",
  "content": "What is knowledge?",
  "cycle": 1
}
```

### Conversation Ended
```json
{
  "type": "conversation_ended",
  "reason": "max_cycles_reached",
  "cycles_completed": 5
}
```

---

## Core Components

### OllamaClient
Handles communication with Ollama LLM servers.

```python
from app.services.ollama_client import OllamaClient
from app.schemas.config import ModelConfig

config = ModelConfig(
    provider="ollama",
    url="http://localhost:11434",
    model_name="llama2",
    thinking=True,
    parameters={"temperature": 0.7}
)

client = OllamaClient(config)
await client.verify_connection()  # Test connection
```

### ConversationState
Manages conversation state throughout execution.

```python
from app.core.state import ConversationStateManager, AgentMessage

# Create initial state
state = ConversationStateManager.create_initial_state("agent_a")

# Add message
msg = AgentMessage(
    content="Hello",
    agent_id="agent_a",
    message_type="ai"
)
state = ConversationStateManager.add_message(state, msg)

# Get messages
messages = ConversationStateManager.get_messages(state)
```

### CycleManager
Tracks cycles and checks termination conditions.

```python
from app.core.cycle_manager import CycleManager

cycle_mgr = CycleManager(
    agent_ids=['agent_a', 'agent_b'],
    max_cycles=5,
    termination_conditions=config.conversation.termination_conditions
)

# Register turns
cycle_mgr.register_agent_turn('agent_a')
cycle_mgr.register_agent_turn('agent_b')

# Check if cycle complete
if cycle_mgr.is_cycle_complete():
    cycle_num = cycle_mgr.complete_cycle()
    
# Check termination
should_terminate, reason = cycle_mgr.check_termination(state)
```

### ThoughtSuppressingCallback
Captures and routes internal reasoning.

```python
from app.core.callbacks import ThoughtSuppressingCallback

callback = ThoughtSuppressingCallback(
    agent_id="agent_a",
    thinking_enabled=True,
    websocket_manager=ws_manager
)

# Use with Ollama client
response = await client.generate_response(
    messages=messages,
    callbacks=[callback]
)

# Get cleaned response
cleaned = callback.get_response_text()
```

---

## Termination Conditions

### Max Cycles
Conversation ends after N complete cycles.

```yaml
conversation:
  max_cycles: 5  # Stop after 5 cycles
```

### Keyword Triggers
Immediate termination when keywords detected.

```yaml
termination_conditions:
  keyword_triggers:
    - "goodbye"
    - "end conversation"
    - "that's all"
```

### Silence Detection
End if no substantive content for N cycles.

```yaml
termination_conditions:
  silence_detection: 3  # Stop after 3 silent cycles
```

---

## Thought Patterns

When `thinking: true` in model config, these patterns are detected and routed to agent console:

- `<thinking>...</thinking>` - XML tags
- ` ```thinking\n...\n``` ` - Markdown code blocks
- `[THINKING:...]` - Bracketed format
- `"Let me think..."` - Natural language

---

## Error Handling

### Connection Errors
```python
from app.services.ollama_client import OllamaConnectionError

try:
    await client.verify_connection()
except OllamaConnectionError as e:
    print(f"Cannot connect to Ollama: {e}")
```

### Timeout Errors
```python
from app.agents.agent_node import AgentTimeoutError

# Timeouts are handled automatically and inject error messages
# Configure timeout in conversation settings:
conversation:
  turn_timeout: 120  # seconds
```

---

## State Persistence

LangGraph uses checkpointing for state persistence:

```python
# State is automatically saved at each step
# Resume from checkpoint:
final_state = await orchestrator.run_conversation(thread_id="conversation-123")
```

---

## Development Tips

### Debug Mode
Enable detailed logging:

```yaml
logging:
  level: "DEBUG"
  include_thoughts: true
  output_directory: "logs/"
```

### Testing Without Ollama
Use the test suite that mocks Ollama responses:

```bash
python /tmp/test_phase2.py
```

### Custom Agent Behavior
Modify persona to change agent behavior:

```yaml
agents:
  agent_a:
    persona: |
      You are a skeptical philosopher who questions everything.
      Always ask "why?" and challenge assumptions.
      Be concise but profound.
```

---

## Next Steps

Phase 2 provides the foundation for agent conversations. Next phases will add:

- **Phase 3**: MCP Server Integration for tool use
- **Phase 4**: Enhanced Web UI with real-time updates
- **Phase 5**: Testing, polish, and deployment

---

## Troubleshooting

### Ollama Not Responding
1. Check Ollama is running: `curl http://localhost:11434/api/tags`
2. Verify model is installed: `ollama list`
3. Test connection: `POST /api/ollama/test-connection`

### Configuration Errors
1. Validate YAML: `POST /api/config/validate`
2. Check agent IDs match
3. Verify all required fields present

### State Issues
1. Check logs for state serialization errors
2. Ensure all messages have required fields
3. Verify conversation_id is unique

---

## Resources

- **Full Documentation**: [PHASE2_SUMMARY.md](../PHASE2_SUMMARY.md)
- **Project Specs**: [PROJECT_SPECS.md](../PROJECT_SPECS.md)
- **Configuration Schema**: `GET /api/config/schema`
- **Example Config**: [config/example-simple.yaml](../config/example-simple.yaml)

---

## Getting Help

1. Check logs: `backend/logs/` (if configured)
2. Review error messages in API responses
3. Use debug logging level
4. Inspect conversation state via API endpoints
