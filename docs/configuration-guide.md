# Configuration Guide

This guide provides comprehensive documentation for configuring the AI Agent Mixer application.

## Configuration File Format

The application uses YAML configuration files with Pydantic validation. All configuration is declarative and version-controlled.

## Complete Configuration Schema

```yaml
version: "1.0"

metadata:
  name: "Configuration Name"
  description: "Brief description"
  author: "Your Name"
  tags: ["tag1", "tag2"]

conversation:
  starting_agent: "agent_a"      # Which agent speaks first
  max_cycles: 10                  # Maximum conversation cycles
  turn_timeout: 300               # Seconds per agent turn
  termination_conditions:
    keyword_triggers:             # Stop on these phrases
      - "goodbye"
      - "end conversation"
    silence_detection: 3          # Stop after N cycles of silence

agents:
  agent_a:
    name: "Agent A"
    persona: |
      You are a friendly AI assistant...
    model:
      provider: "ollama"
      url: "http://localhost:11434"
      model_name: "llama2"
      thinking: false               # Enable thought streaming
      parameters:
        temperature: 0.7
        top_p: 0.9
    mcp_servers: []                 # Agent-specific MCP servers

  agent_b:
    name: "Agent B"
    persona: |
      You are a knowledgeable expert...
    model:
      provider: "ollama"
      url: "http://localhost:11434"
      model_name: "mistral"
      thinking: true
      parameters:
        temperature: 0.8
    mcp_servers: ["search"]

mcp_servers:
  global_servers:
    - name: "filesystem"
      command: "mcp-server-filesystem"
      args: ["/tmp"]
      env:
        ALLOWED_PATHS: "/tmp,/data"
    - name: "search"
      command: "mcp-server-brave-search"
      args: []
      env:
        BRAVE_API_KEY: "${BRAVE_API_KEY}"

initialization:
  system_prompt_template: |
    You are {{ agent.name }}.
    
    {{ agent.persona }}
    
    Available tools: {{ tools }}
  first_message: "Hello! Let's discuss AI."

logging:
  level: "INFO"                    # DEBUG, INFO, WARNING, ERROR, CRITICAL
  include_thoughts: true
  output_directory: "/var/log/ai-agent-mixer"
```

## Configuration Sections

### 1. Metadata (Optional)

Arbitrary information about the configuration.

```yaml
metadata:
  name: "Philosophy Debate"
  description: "Two agents discuss philosophical concepts"
  author: "Jane Doe"
  created: "2024-01-15"
  tags: ["philosophy", "debate", "socratic"]
```

**Fields**:
- `name`: Human-readable configuration name
- `description`: Brief purpose description
- `author`: Configuration creator
- Any additional fields you want

### 2. Conversation Settings

Controls conversation flow and termination.

```yaml
conversation:
  starting_agent: "agent_a"       # Required: agent ID
  max_cycles: 10                   # Required: 1-1000
  turn_timeout: 300                # Required: seconds (1-3600)
  termination_conditions:          # Optional
    keyword_triggers:              # Optional: list of strings
      - "goodbye"
      - "exit"
      - "end"
    silence_detection: 3           # Optional: number of cycles
```

**Fields**:
- `starting_agent`: Must match an agent ID in `agents` section
- `max_cycles`: Hard limit on conversation length
- `turn_timeout`: Maximum seconds for one agent turn
- `termination_conditions.keyword_triggers`: Case-insensitive phrase matching
- `termination_conditions.silence_detection`: Cycles without substantive content (>20 chars)

**Examples**:
```yaml
# Short experiment
conversation:
  starting_agent: "agent_a"
  max_cycles: 3
  turn_timeout: 60

# Long conversation with multiple exit conditions
conversation:
  starting_agent: "researcher"
  max_cycles: 50
  turn_timeout: 600
  termination_conditions:
    keyword_triggers:
      - "conclusion reached"
      - "study complete"
    silence_detection: 5
```

### 3. Agent Configuration

Define each agent's personality, model, and tools.

```yaml
agents:
  agent_id:                        # Unique identifier
    name: "Display Name"           # Required
    persona: "System prompt..."    # Required: multiline string
    model:                         # Required
      provider: "ollama"           # Currently only "ollama"
      url: "http://..."            # Required: must start with http:// or https://
      model_name: "model"          # Required: alphanumeric, _, -, ., :
      thinking: false              # Optional: default false
      parameters:                  # Optional
        temperature: 0.7           # 0.0-1.0
        top_p: 0.9                 # 0.0-1.0
        top_k: 40                  # integer
        repeat_penalty: 1.1        # float
    mcp_servers: []                # Optional: list of MCP server names
```

**Model Parameters**:
- `temperature`: Randomness (0.0 = deterministic, 1.0 = creative)
- `top_p`: Nucleus sampling threshold
- `top_k`: Top-K sampling limit
- `repeat_penalty`: Penalize repetition

**Thinking Mode**:
When `thinking: true`:
- Internal reasoning streamed to agent console (left/right panels)
- Final response filtered to remove thought artifacts
- Useful for debugging agent decision-making

**Examples**:
```yaml
# Research assistant with thinking
agents:
  researcher:
    name: "Research Assistant"
    persona: |
      You are a meticulous researcher who:
      - Cites sources for all claims
      - Considers multiple perspectives
      - Admits uncertainty when appropriate
    model:
      url: "http://ollama:11434"
      model_name: "llama2:13b"
      thinking: true
      parameters:
        temperature: 0.3  # More focused
        top_p: 0.85
    mcp_servers: ["filesystem", "search"]

# Creative writer without thinking
agents:
  writer:
    name: "Creative Writer"
    persona: |
      You are a creative storyteller who:
      - Uses vivid imagery
      - Builds suspense
      - Surprises readers
    model:
      url: "http://localhost:11434"
      model_name: "mistral"
      thinking: false
      parameters:
        temperature: 0.9  # More creative
        top_p: 0.95
    mcp_servers: []
```

### 4. MCP Server Configuration

Define external tools available to agents.

```yaml
mcp_servers:
  global_servers:                  # Available to all agents
    - name: "server_id"            # Required: alphanumeric, _, -
      command: "executable"        # Required: command to run
      args: ["arg1", "arg2"]       # Optional: list of strings
      env:                         # Optional: environment variables
        KEY: "value"
        SECRET: "${ENV_VAR}"       # Use environment variable
```

**Global vs Agent-Scoped**:
- **Global servers**: Defined in `mcp_servers.global_servers`, available to all agents
- **Agent-scoped servers**: Listed in `agents.{id}.mcp_servers`, only available to that agent

**Environment Variables**:
Use `${VAR_NAME}` syntax to substitute from environment:
```yaml
env:
  API_KEY: "${BRAVE_API_KEY}"     # Reads from environment
  STATIC: "hardcoded-value"       # Literal value
```

**Examples**:
```yaml
# Filesystem access (read-only)
mcp_servers:
  global_servers:
    - name: "filesystem"
      command: "mcp-server-filesystem"
      args: ["/data"]
      env:
        ALLOWED_PATHS: "/data,/tmp"
        READ_ONLY: "true"

# Search capability
mcp_servers:
  global_servers:
    - name: "search"
      command: "mcp-server-brave-search"
      args: []
      env:
        BRAVE_API_KEY: "${BRAVE_API_KEY}"

# Database access (agent-scoped)
agents:
  data_analyst:
    name: "Data Analyst"
    persona: "..."
    model: {...}
    mcp_servers: ["database"]  # Only this agent can access

mcp_servers:
  global_servers:
    - name: "database"
      command: "mcp-server-postgres"
      args: []
      env:
        DB_HOST: "${POSTGRES_HOST}"
        DB_USER: "${POSTGRES_USER}"
        DB_PASSWORD: "${POSTGRES_PASSWORD}"
```

### 5. Initialization

Control how conversations start.

```yaml
initialization:
  system_prompt_template: |        # Optional: Jinja2 template
    You are {{ agent.name }}.
    
    {{ agent.persona }}
    
    {% if tools %}
    Available tools: {{ tools }}
    {% endif %}
  first_message: "Hello!"          # Required: initial message
```

**System Prompt Template**:
Jinja2 template with variables:
- `{{ agent.name }}`: Agent display name
- `{{ agent.persona }}`: Agent persona text
- `{{ tools }}`: List of available tool names

**First Message**:
Kick-starts the conversation. Attributed to `starting_agent`.

**Examples**:
```yaml
# Minimal
initialization:
  first_message: "Let's begin."

# Custom template
initialization:
  system_prompt_template: |
    # {{ agent.name }}
    
    ## Role
    {{ agent.persona }}
    
    ## Instructions
    - Be concise
    - Ask clarifying questions
    - Use tools when helpful
    
    ## Available Tools
    {% for tool in tools %}
    - {{ tool }}
    {% endfor %}
  first_message: "What shall we discuss today?"
```

### 6. Logging Configuration

Control application logging behavior.

```yaml
logging:
  level: "INFO"                    # Required: DEBUG, INFO, WARNING, ERROR, CRITICAL
  include_thoughts: true           # Optional: default true
  output_directory: "/var/log"    # Optional: default null (stdout only)
```

**Log Levels**:
- `DEBUG`: Verbose, includes all state transitions
- `INFO`: Normal operation, major events
- `WARNING`: Unusual but handled conditions
- `ERROR`: Errors that don't stop execution
- `CRITICAL`: Fatal errors

**Include Thoughts**:
Whether to log thought messages to files. Always streamed to WebSocket regardless.

**Output Directory**:
If specified, logs written to files. If `null`, logs to stdout only.

**Examples**:
```yaml
# Development
logging:
  level: "DEBUG"
  include_thoughts: true
  output_directory: "./logs"

# Production
logging:
  level: "INFO"
  include_thoughts: false
  output_directory: "/var/log/ai-agent-mixer"
```

## Environment Variables

### Substitution Syntax

Use `${VARIABLE_NAME}` in configuration:

```yaml
model:
  url: "${OLLAMA_URL}"  # Replaced at runtime
env:
  API_KEY: "${BRAVE_API_KEY}"
```

### Required Variables

None by default. Variables depend on your configuration:

```bash
# For Ollama URLs
export OLLAMA_URL="http://ollama-server:11434"

# For MCP server credentials
export BRAVE_API_KEY="your_key_here"
export POSTGRES_PASSWORD="secret"
```

### Docker Compose Environment

Set in `docker-compose.yml`:

```yaml
services:
  backend:
    environment:
      - OLLAMA_URL=http://ollama:11434
      - BRAVE_API_KEY=${BRAVE_API_KEY}  # Pass from host
```

Or in `.env` file:
```bash
OLLAMA_URL=http://localhost:11434
BRAVE_API_KEY=sk-...
```

## Validation

### Runtime Validation

All configuration is validated on import:

```python
# Returns validation errors with line numbers
POST /api/config/validate
Content-Type: text/plain

<yaml content>
```

Response:
```json
{
  "valid": false,
  "errors": [
    "conversation -> starting_agent: Starting agent 'nonexistent' not found in agents",
    "agents -> agent_a -> model -> url: URL must start with http:// or https://"
  ]
}
```

### Common Validation Errors

1. **Missing required fields**:
   ```
   agents -> agent_a -> name: field required
   ```

2. **Invalid agent reference**:
   ```
   conversation -> starting_agent: Starting agent 'xyz' not found in agents
   ```

3. **Invalid URL format**:
   ```
   agents -> agent_a -> model -> url: URL must start with http:// or https://
   ```

4. **Invalid model name**:
   ```
   agents -> agent_a -> model -> model_name: Model name can only contain alphanumeric characters, _, -, ., and :
   ```

5. **Insufficient agents**:
   ```
   agents: At least two agents must be configured
   ```

## Configuration Examples

### Example 1: Simple Two-Agent Conversation

```yaml
version: "1.0"
conversation:
  starting_agent: "alice"
  max_cycles: 5
agents:
  alice:
    name: "Alice"
    persona: "You are friendly and curious."
    model:
      url: "http://localhost:11434"
      model_name: "llama2"
  bob:
    name: "Bob"
    persona: "You are knowledgeable and patient."
    model:
      url: "http://localhost:11434"
      model_name: "llama2"
initialization:
  first_message: "What's your favorite color?"
```

### Example 2: Research Collaboration with Tools

```yaml
version: "1.0"
metadata:
  name: "Research Partnership"
conversation:
  starting_agent: "researcher"
  max_cycles: 20
  turn_timeout: 600
  termination_conditions:
    keyword_triggers: ["research complete"]
agents:
  researcher:
    name: "Lead Researcher"
    persona: |
      You conduct thorough research using available tools.
      You cite sources and verify information.
    model:
      url: "http://ollama:11434"
      model_name: "llama2:13b"
      thinking: true
      parameters:
        temperature: 0.3
    mcp_servers: ["filesystem", "search"]
  
  analyst:
    name: "Data Analyst"
    persona: |
      You analyze data and provide statistical insights.
      You validate research findings.
    model:
      url: "http://ollama:11434"
      model_name: "mistral"
      thinking: true
      parameters:
        temperature: 0.5
    mcp_servers: ["filesystem"]

mcp_servers:
  global_servers:
    - name: "filesystem"
      command: "mcp-server-filesystem"
      args: ["/data"]
    - name: "search"
      command: "mcp-server-brave-search"
      env:
        BRAVE_API_KEY: "${BRAVE_API_KEY}"

initialization:
  first_message: "Let's research the impact of AI on employment."
```

### Example 3: Creative Writing Session

```yaml
version: "1.0"
metadata:
  name: "Story Collaboration"
conversation:
  starting_agent: "plot_writer"
  max_cycles: 15
  termination_conditions:
    keyword_triggers: ["THE END"]
    silence_detection: 3
agents:
  plot_writer:
    name: "Plot Developer"
    persona: |
      You create engaging story structures with:
      - Clear three-act structure
      - Character development arcs
      - Compelling conflicts
    model:
      url: "http://localhost:11434"
      model_name: "llama2"
      parameters:
        temperature: 0.8
  
  character_writer:
    name: "Character Specialist"
    persona: |
      You develop rich, believable characters with:
      - Distinct personalities
      - Realistic motivations
      - Memorable dialogue
    model:
      url: "http://localhost:11434"
      model_name: "mistral"
      parameters:
        temperature: 0.9

initialization:
  first_message: "Let's write a sci-fi short story about first contact."
```

## Best Practices

### 1. Persona Design
- Be specific and detailed
- Include behavioral guidelines
- Specify knowledge domains
- Define interaction style

### 2. Model Selection
- Use larger models for complex reasoning
- Use smaller models for simple tasks
- Match temperature to task (low for factual, high for creative)

### 3. Tool Assignment
- Give relevant tools to agents who need them
- Use global servers for common capabilities
- Use agent-scoped servers for specialized access

### 4. Termination Conditions
- Set realistic max_cycles based on task
- Include explicit termination keywords
- Use silence detection for open-ended conversations

### 5. Security
- Never hardcode secrets in YAML
- Use environment variables for credentials
- Restrict filesystem access to necessary paths
- Validate all configuration before deployment

## Troubleshooting

### Configuration won't load
- Check YAML syntax (indentation, quotes)
- Verify all required fields present
- Ensure agent IDs match references
- Check URL formats

### Agent won't connect to Ollama
- Verify URL is correct
- Ensure model is pulled: `ollama pull llama2`
- Check network connectivity
- Review Ollama logs

### MCP server fails to start
- Verify command exists: `which mcp-server-filesystem`
- Check environment variables are set
- Review server logs in application output
- Test server manually

### Conversation terminates unexpectedly
- Check termination condition keywords
- Review max_cycles setting
- Look for timeout errors in logs
- Verify agent responses aren't silent

## JSON Schema

Get the full JSON schema for IDE autocomplete:

```bash
curl http://localhost:8000/api/config/schema > config-schema.json
```

Then configure your IDE to validate YAML against the schema.
