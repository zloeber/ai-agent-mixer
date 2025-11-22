# Multi-Scenario Configuration

## Overview

The AI Agent Mixer now supports defining multiple conversation scenarios in a single configuration file. This allows you to:

- Define different conversation goals for the same set of agents
- Control which agents participate in each scenario
- Adjust conversation parameters (brevity, max cycles) per scenario
- Easily switch between scenarios in the UI

## Configuration Schema

### ConversationScenario

Each scenario has the following properties:

```yaml
conversations:
  - name: "Scenario Name"           # Unique identifier (required)
    goal: "Conversation objective"   # What agents should discuss (required)
    brevity: "short|medium|long"     # Response length guidance (required)
    max_cycles: 10                   # Maximum turns (default: 5)
    starting_agent: "agent_id"       # First agent to speak (default: first agent)
    agents_involved:                 # Optional: filter agents for this scenario
      - agent_id_1
      - agent_id_2
    turn_timeout: 120                # Seconds per turn (default: 120)
    termination_conditions:          # Optional: override global conditions
      keyword_triggers:
        - "goodbye"
        - "exit"
```

### Backward Compatibility

The legacy `conversation` single-scenario format is still supported:

```yaml
conversation:
  starting_agent: "agent_a"
  max_cycles: 5
  turn_timeout: 120
  termination_conditions:
    keyword_triggers: ["goodbye", "exit"]
```

If both `conversation` and `conversations` are present, `conversations` takes precedence.

## Example Configuration

```yaml
version: "1.0"

metadata:
  name: "Multi-Scenario AI Exchange"

agents:
  researcher:
    name: "Research Assistant"
    persona: "Academic researcher focused on factual analysis"
    model:
      url: "http://localhost:11434"
      model_name: "llama3.2:latest"
  
  analyst:
    name: "Strategic Analyst"
    persona: "Business analyst identifying practical implications"
    model:
      url: "http://localhost:11434"
      model_name: "mistral:latest"
  
  optimist:
    name: "Optimistic Thinker"
    persona: "Positive, enthusiastic, sees potential"
    model:
      url: "http://localhost:11434"
      model_name: "llama3.2:latest"
  
  realist:
    name: "Pragmatic Realist"
    persona: "Practical, grounded, considers constraints"
    model:
      url: "http://localhost:11434"
      model_name: "mistral:latest"

# Define multiple conversation scenarios
conversations:
  - name: "Research and Synthesis"
    goal: "Explore a topic through research and strategic analysis"
    brevity: "medium"
    max_cycles: 8
    starting_agent: "researcher"
    agents_involved:
      - researcher
      - analyst
    termination_conditions:
      keyword_triggers:
        - "conclusion"
        - "summary complete"
  
  - name: "Opposites Debate"
    goal: "Debate different perspectives on a controversial topic"
    brevity: "short"
    max_cycles: 10
    starting_agent: "optimist"
    agents_involved:
      - optimist
      - realist
    termination_conditions:
      keyword_triggers:
        - "agree to disagree"
        - "compromise"

initialization:
  first_message: "What are the implications of AI in education?"
  system_prompt_template: |
    You are {{ agent.name }}, {{ agent.persona }}.
    
    Conversation Goal: {{ conversation.goal }}
    Keep responses {{ conversation.brevity }}.
    
    {% if conversation.scenario_name %}
    Scenario: {{ conversation.scenario_name }}
    {% endif %}

logging:
  level: "INFO"
  include_thoughts: true
```

## API Endpoints

### List Scenarios

```http
GET /api/conversation/scenarios
```

Response:
```json
{
  "scenarios": [
    {
      "name": "Research and Synthesis",
      "goal": "Explore a topic through research and strategic analysis",
      "brevity": "medium",
      "max_cycles": 8,
      "starting_agent": "researcher",
      "agents_involved": ["researcher", "analyst"]
    },
    {
      "name": "Opposites Debate",
      "goal": "Debate different perspectives on a controversial topic",
      "brevity": "short",
      "max_cycles": 10,
      "starting_agent": "optimist",
      "agents_involved": ["optimist", "realist"]
    }
  ],
  "default": "Research and Synthesis"
}
```

### Start Conversation with Scenario

```http
POST /api/conversation/start?scenario=Research%20and%20Synthesis
```

Response:
```json
{
  "status": "started",
  "scenario": "Research and Synthesis",
  "conversation_id": "uuid",
  "started_at": "2024-01-01T12:00:00Z",
  "agents": ["researcher", "analyst"],
  "max_cycles": 8
}
```

## UI Integration

The frontend `ControlPanel` component automatically:

1. **Fetches available scenarios** when a configuration is loaded
2. **Displays a scenario selector** dropdown when scenarios are available
3. **Passes the selected scenario** to the start endpoint
4. **Shows scenario information** in the UI

### Scenario Selector

When scenarios are available, a dropdown appears in the control panel:

```
Scenario: [Research and Synthesis ▼]
```

Selecting a different scenario changes the conversation parameters for the next run.

## Template Variables

Scenarios expose additional template variables for customization:

- `{{ conversation.scenario_name }}` - Name of the current scenario
- `{{ conversation.goal }}` - Scenario-specific goal
- `{{ conversation.brevity }}` - Response length guidance
- `{{ conversation.max_cycles }}` - Maximum cycles for this scenario
- `{{ conversation.agents_involved }}` - List of agents in scenario (if specified)

## Agent Filtering

### All Agents (Default)

If `agents_involved` is not specified, all configured agents participate:

```yaml
conversations:
  - name: "Open Discussion"
    goal: "Free-form conversation"
    # No agents_involved - all agents participate
```

### Filtered Agents

Specify `agents_involved` to limit participation:

```yaml
conversations:
  - name: "Expert Panel"
    goal: "Technical deep dive"
    agents_involved:
      - expert_1
      - expert_2
    # Other agents are excluded from this scenario
```

**Note**: `starting_agent` must be in `agents_involved` if specified.

## Validation

The configuration validator checks:

1. **Unique scenario names** - No duplicate scenario names
2. **Valid starting agents** - Starting agent exists in agents config
3. **Valid agents_involved** - All listed agents exist in agents config
4. **At least one scenario** - Either `conversation` or non-empty `conversations` required
5. **Starting agent in scenario** - If `agents_involved` specified, `starting_agent` must be included

## Migration from Legacy Format

To migrate from single `conversation` to multiple `conversations`:

### Before (Legacy)
```yaml
conversation:
  starting_agent: "agent_a"
  max_cycles: 5
  termination_conditions:
    keyword_triggers: ["goodbye"]
```

### After (Multi-Scenario)
```yaml
conversations:
  - name: "Default Conversation"
    goal: "General discussion"
    brevity: "medium"
    starting_agent: "agent_a"
    max_cycles: 5
    termination_conditions:
      keyword_triggers: ["goodbye"]
```

The system automatically handles both formats, so you can upgrade incrementally.

## Best Practices

1. **Descriptive names** - Use clear, distinct scenario names
2. **Specific goals** - Each scenario should have a focused objective
3. **Agent selection** - Match agents to scenario goals (optional but recommended)
4. **Brevity settings** - Adjust based on scenario complexity
   - `short`: Quick exchanges, debates
   - `medium`: Standard discussions
   - `long`: Deep analysis, research
5. **Max cycles** - Set based on expected conversation depth
6. **Termination keywords** - Use scenario-specific exit phrases

## Troubleshooting

### Scenario not appearing in UI

- Check configuration is loaded (`/health` endpoint shows `config_loaded: true`)
- Verify YAML syntax is valid
- Ensure scenarios have unique names

### Wrong agents participating

- Check `agents_involved` list in scenario
- Verify agent IDs match those in `agents` section
- Confirm `starting_agent` is in `agents_involved` (if specified)

### Templates not showing scenario variables

- Ensure template uses Jinja2 syntax: `{{ conversation.scenario_name }}`
- Check template is set in `initialization.system_prompt_template`
- Verify scenario is being passed to orchestrator

## Implementation Details

### Backend Flow

1. **Configuration loading** - `RootConfig.get_conversation_config(scenario_name)` returns scenario
2. **Orchestrator initialization** - `ConversationOrchestrator(config, scenario_name=...)` sets up workflow
3. **Agent filtering** - `_build_graph()` creates nodes only for involved agents
4. **Context passing** - `ConversationInitializer` exposes scenario info to templates

### State Tracking

Conversation state includes scenario metadata:

```python
state["metadata"]["scenario_name"] = scenario_name
```

This allows tracking which scenario was used for each conversation.
