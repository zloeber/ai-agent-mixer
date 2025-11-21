# API Reference

Complete documentation for the AI Agent Mixer REST API and WebSocket endpoints.

## Base URL

```
http://localhost:8000
```

## Authentication

Currently no authentication required (development mode).

## Content Types

- Request: `application/json` or `multipart/form-data` (file uploads)
- Response: `application/json`

---

## Health & Monitoring

### GET /health

Health check endpoint.

**Response**:
```json
{
  "status": "healthy",
  "config_loaded": true
}
```

### GET /metrics

Prometheus-compatible metrics endpoint.

**Response** (text/plain):
```
requests_total 150
requests_errors 5
conversations_started 10
conversations_completed 8
websocket_connections_active 3
mcp_servers_total 2
mcp_servers_healthy 2
conversation_running 0
```

---

## Configuration Management

### POST /api/config/import

Import configuration from JSON object.

**Request**:
```json
{
  "version": "1.0",
  "conversation": {
    "starting_agent": "agent_a",
    "max_cycles": 5
  },
  "agents": {
    "agent_a": {...},
    "agent_b": {...}
  },
  "initialization": {
    "first_message": "Hello"
  }
}
```

**Response**:
```json
{
  "status": "success",
  "message": "Configuration imported successfully",
  "agents": ["agent_a", "agent_b"],
  "starting_agent": "agent_a",
  "mcp_servers": {
    "started": ["filesystem"],
    "failed": [],
    "total": 1
  }
}
```

**Errors**:
- 422: Validation failed
- 400: Import failed

### POST /api/config/upload

Upload YAML configuration file.

**Request** (multipart/form-data):
```
file: config.yaml
```

**Response**:
```json
{
  "status": "success",
  "message": "Configuration from config.yaml imported successfully",
  "agents": ["agent_a", "agent_b"],
  "starting_agent": "agent_a"
}
```

### GET /api/config/export

Export current configuration as JSON.

**Response**:
```json
{
  "version": "1.0",
  "conversation": {...},
  "agents": {...},
  ...
}
```

**Errors**:
- 404: No configuration loaded

### POST /api/config/validate

Validate YAML configuration content.

**Request** (text/plain):
```yaml
version: "1.0"
conversation:
  starting_agent: "agent_a"
...
```

**Response**:
```json
{
  "valid": true,
  "errors": []
}
```

Or if invalid:
```json
{
  "valid": false,
  "errors": [
    "conversation -> starting_agent: field required",
    "agents: At least two agents must be configured"
  ]
}
```

### GET /api/config/schema

Get JSON schema for configuration validation.

**Response**:
```json
{
  "$defs": {...},
  "properties": {...},
  "required": [...],
  "title": "RootConfig",
  "type": "object"
}
```

---

## Conversation Management

### POST /api/conversation/start

Start a new conversation.

**Preconditions**:
- Configuration must be loaded
- No conversation currently running

**Response**:
```json
{
  "status": "started",
  "conversation_id": "conv-123",
  "starting_agent": "agent_a",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

**Errors**:
- 400: No configuration loaded or conversation already running
- 500: Failed to start

### POST /api/conversation/stop

Stop the current conversation.

**Response**:
```json
{
  "status": "stopped",
  "message": "Conversation stopped"
}
```

**Errors**:
- 400: No conversation running

### POST /api/conversation/pause

Pause the current conversation.

**Response**:
```json
{
  "status": "paused",
  "message": "Conversation paused"
}
```

**Errors**:
- 400: No conversation running

### POST /api/conversation/resume

Resume a paused conversation.

**Response**:
```json
{
  "status": "resumed",
  "message": "Conversation resumed"
}
```

**Errors**:
- 400: No conversation running or not paused

### GET /api/conversation/status

Get current conversation status.

**Response** (running):
```json
{
  "running": true,
  "current_cycle": 3,
  "message_count": 12,
  "should_terminate": false,
  "termination_reason": null
}
```

**Response** (not running):
```json
{
  "running": false,
  "message": "No conversation running"
}
```

---

## MCP Server Management

### GET /api/mcp/status

Get status of all MCP servers.

**Response**:
```json
{
  "servers": {
    "filesystem": {
      "running": true,
      "healthy": true,
      "started_at": "2024-01-01T12:00:00Z",
      "error_message": null,
      "tools_count": 5,
      "tools": ["read_file", "write_file", ...]
    },
    "search": {
      "running": false,
      "healthy": false,
      "started_at": null,
      "error_message": "Connection failed",
      "tools_count": 0,
      "tools": []
    }
  },
  "total_servers": 2,
  "healthy_servers": 1
}
```

### GET /api/mcp/servers/{server_name}/status

Get status of specific MCP server.

**Response**:
```json
{
  "name": "filesystem",
  "running": true,
  "healthy": true,
  "started_at": "2024-01-01T12:00:00Z",
  "error_message": null,
  "tools_count": 5,
  "tools": ["read_file", "write_file", "list_directory", "create_directory", "delete_file"]
}
```

**Errors**:
- 404: Server not found

### POST /api/mcp/servers/{server_name}/restart

Restart a specific MCP server.

**Response**:
```json
{
  "status": "success",
  "message": "Server filesystem restarted successfully"
}
```

**Errors**:
- 500: Restart failed

### GET /api/mcp/tools

Get all available tools from all MCP servers.

**Response**:
```json
{
  "tools": [
    {
      "name": "read_file",
      "description": "Read contents of a file",
      "server": "filesystem",
      "input_schema": {
        "type": "object",
        "properties": {
          "path": {"type": "string"}
        },
        "required": ["path"]
      }
    },
    {
      "name": "brave_search",
      "description": "Search the web using Brave Search",
      "server": "search",
      "input_schema": {...}
    }
  ],
  "total_count": 2
}
```

### GET /api/mcp/agents/{agent_id}/tools

Get tools available to a specific agent.

**Response**:
```json
{
  "agent_id": "agent_a",
  "tools": [
    {"name": "read_file", ...},
    {"name": "search", ...}
  ],
  "total_count": 2,
  "global_servers": ["filesystem"],
  "agent_servers": ["search"]
}
```

**Errors**:
- 404: No configuration loaded or agent not found

---

## Ollama Testing

### POST /api/ollama/test-connection

Test connection to Ollama instance.

**Request**:
```json
{
  "provider": "ollama",
  "url": "http://localhost:11434",
  "model_name": "llama2"
}
```

**Response** (success):
```json
{
  "status": "success",
  "message": "Successfully connected to http://localhost:11434 with model llama2",
  "url": "http://localhost:11434",
  "model": "llama2"
}
```

**Response** (error):
```json
{
  "status": "error",
  "message": "Connection refused",
  "url": "http://localhost:11434"
}
```

---

## WebSocket API

### WS /ws/{client_id}

WebSocket endpoint for real-time communication.

**Connection**:
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/client-123');
```

**On Connect**:
Server sends:
```json
{
  "type": "connected",
  "message": "Connected to AI Agent Mixer",
  "client_id": "client-123"
}
```

### Message Types

#### Thought Message
Agent internal reasoning (when `thinking: true`):
```json
{
  "type": "thought",
  "agent_id": "agent_a",
  "content": "I think the best approach is...",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

#### Conversation Message
Agent response in conversation:
```json
{
  "type": "message",
  "agent_id": "agent_a",
  "content": "Based on the data, I conclude...",
  "timestamp": "2024-01-01T12:00:00Z",
  "cycle": 3
}
```

#### Tool Call
Tool execution notification:
```json
{
  "type": "tool_call",
  "agent_id": "agent_a",
  "tool_name": "search",
  "arguments": {"query": "AI trends"},
  "timestamp": "2024-01-01T12:00:00Z"
}
```

#### Tool Result
Tool execution result:
```json
{
  "type": "tool_result",
  "tool_name": "search",
  "result": "Found 10 results...",
  "duration_ms": 250,
  "timestamp": "2024-01-01T12:00:00Z"
}
```

#### Cycle Update
Conversation cycle progression:
```json
{
  "type": "cycle_update",
  "cycle": 4,
  "max_cycles": 10,
  "agents_spoken": ["agent_a", "agent_b"]
}
```

#### Conversation Status
Status change notification:
```json
{
  "type": "conversation_status",
  "status": "running",  // or "paused", "stopped"
  "timestamp": "2024-01-01T12:00:00Z"
}
```

#### Conversation Ended
Conversation termination:
```json
{
  "type": "conversation_ended",
  "reason": "max_cycles_reached",  // or "keyword_trigger", "stopped_by_user"
  "cycles_completed": 10,
  "message_count": 25,
  "timestamp": "2024-01-01T12:00:00Z"
}
```

#### Error
Error notification:
```json
{
  "type": "error",
  "error": "AgentTimeoutError",
  "message": "Agent 'agent_a' timed out",
  "details": {"agent_id": "agent_a", "timeout": 300}
}
```

### Heartbeat

**Client sends**:
```json
{"type": "ping"}
```

**Server responds**:
```json
{"type": "pong"}
```

### GET /api/ws/status

Get WebSocket connection status.

**Response**:
```json
{
  "active_connections": 3
}
```

---

## Error Responses

All error responses follow this format:

```json
{
  "error": "ConfigurationError",
  "message": "Invalid configuration provided",
  "details": {
    "field": "agents",
    "issue": "At least two agents required"
  }
}
```

### HTTP Status Codes

- **200**: Success
- **400**: Bad request (invalid input)
- **404**: Resource not found
- **422**: Validation error
- **500**: Internal server error
- **503**: Service unavailable (e.g., Ollama connection failed)

---

## Rate Limiting

Currently no rate limiting implemented.

## CORS

Allowed origins (configurable):
- `http://localhost:3000`
- `http://localhost:5173`
- `http://127.0.0.1:3000`
- `http://127.0.0.1:5173`

---

## Example Workflows

### Complete Conversation Flow

1. **Upload config**:
```bash
curl -X POST http://localhost:8000/api/config/upload \
  -F "file=@config.yaml"
```

2. **Verify MCP servers**:
```bash
curl http://localhost:8000/api/mcp/status
```

3. **Connect WebSocket**:
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/my-client');
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data.type, data);
};
```

4. **Start conversation**:
```bash
curl -X POST http://localhost:8000/api/conversation/start
```

5. **Monitor progress** (via WebSocket messages)

6. **Check status**:
```bash
curl http://localhost:8000/api/conversation/status
```

### Configuration Validation

```bash
# Validate before uploading
curl -X POST http://localhost:8000/api/config/validate \
  -H "Content-Type: text/plain" \
  --data-binary @config.yaml
```

### Testing Ollama Connection

```bash
curl -X POST http://localhost:8000/api/ollama/test-connection \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "ollama",
    "url": "http://localhost:11434",
    "model_name": "llama2"
  }'
```

---

## SDK Examples

### Python

```python
import requests
import json

# Upload config
with open('config.yaml', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/api/config/upload',
        files={'file': f}
    )
print(response.json())

# Start conversation
response = requests.post('http://localhost:8000/api/conversation/start')
print(response.json())
```

### JavaScript

```javascript
// Upload config
const formData = new FormData();
formData.append('file', fileInput.files[0]);

const response = await fetch('http://localhost:8000/api/config/upload', {
  method: 'POST',
  body: formData
});
const data = await response.json();

// WebSocket connection
const ws = new WebSocket('ws://localhost:8000/ws/client-id');
ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);
  handleMessage(msg);
};
```

### cURL

```bash
# Health check
curl http://localhost:8000/health

# Get metrics
curl http://localhost:8000/metrics

# Export config
curl http://localhost:8000/api/config/export > config.json

# Stop conversation
curl -X POST http://localhost:8000/api/conversation/stop
```
