# Phase 6 Summary: Multi-Scenario Configuration Support

## Overview

Phase 6 adds support for defining multiple conversation scenarios in a single configuration file. This feature enables users to:

- Define different conversation goals and parameters for various use cases
- Control which agents participate in specific scenarios
- Easily switch between scenarios through the UI
- Maintain backward compatibility with legacy single-scenario configurations

## Implementation Date

January 2025

## Key Features

### 1. Multi-Scenario Schema

**New ConversationScenario Model**
- `name`: Unique identifier for the scenario
- `goal`: What the conversation should accomplish
- `brevity`: Response length guidance (short/medium/long)
- `max_cycles`: Maximum conversation turns
- `starting_agent`: First agent to speak
- `agents_involved`: Optional agent filtering
- `turn_timeout`: Seconds per turn
- `termination_conditions`: Scenario-specific exit conditions

**Configuration Structure**
```yaml
conversations:
  - name: "Research and Synthesis"
    goal: "Explore topic through research and analysis"
    brevity: "medium"
    agents_involved: [researcher, analyst]
    # ... other settings
  
  - name: "Opposites Debate"
    goal: "Debate different perspectives"
    brevity: "short"
    agents_involved: [optimist, realist]
    # ... other settings
```

### 2. Backend API Updates

**New Endpoints**

`GET /api/conversation/scenarios`
- Lists all available scenarios
- Returns scenario details (name, goal, brevity, agents, etc.)
- Identifies default scenario

`POST /api/conversation/start?scenario=name`
- Starts conversation with selected scenario
- Falls back to first scenario if none specified
- Returns scenario information in response

**Updated Components**

- **ConversationOrchestrator**: Accepts `scenario_name` parameter, filters agents based on scenario
- **ConversationInitializer**: Passes scenario context to templates
- **RootConfig**: New methods `get_conversation_config()` and `list_scenarios()`

### 3. Frontend UI Integration

**ControlPanel Enhancements**
- Scenario selector dropdown when scenarios available
- Automatic scenario list fetching on config load
- Scenario information display
- Selected scenario passed to start endpoint

**User Experience**
- Seamless scenario switching
- Visual scenario selection
- Scenario-specific settings reflected in UI

### 4. Template Context Expansion

New template variables for scenario customization:
- `{{ conversation.scenario_name }}`
- `{{ conversation.goal }}`
- `{{ conversation.brevity }}`
- `{{ conversation.agents_involved }}`

Example usage:
```jinja2
Scenario: {{ conversation.scenario_name }}
Goal: {{ conversation.goal }}
Keep responses {{ conversation.brevity }}.
```

### 5. Backward Compatibility

**Legacy Support**
- Single `conversation` field still supported
- Automatic conversion to scenario format
- No breaking changes to existing configurations
- Tests confirm backward compatibility (26/26 passing)

**Migration Path**
- Users can upgrade incrementally
- Both formats work side-by-side
- `conversations` takes precedence if both present

## Files Modified

### Backend
- `backend/app/schemas/config.py` - Added ConversationScenario model and helper methods
- `backend/app/core/orchestrator.py` - Scenario selection and agent filtering
- `backend/app/services/initializer.py` - Scenario context passing
- `backend/app/main.py` - New scenarios endpoint, updated start endpoint

### Frontend
- `frontend/src/components/ControlPanel.tsx` - Scenario selector UI

### Documentation
- `docs/MULTI_SCENARIO.md` - Comprehensive feature guide
- `config/multi-scenario-example.yaml` - Example configuration

## Technical Highlights

### Agent Filtering Implementation

The orchestrator now filters agents based on `agents_involved`:

```python
if hasattr(self.conversation_config, 'agents_involved') and self.conversation_config.agents_involved:
    active_agents = {
        agent_id: agent_config
        for agent_id, agent_config in self.config.agents.items()
        if agent_id in self.conversation_config.agents_involved
    }
else:
    active_agents = self.config.agents
```

### Scenario Selection Pattern

```python
# Get conversation config dynamically
conversation_config = config.get_conversation_config(scenario_name)

# Pass to orchestrator
orchestrator = ConversationOrchestrator(
    config=config,
    scenario_name=scenario_name
)
```

### State Metadata Tracking

```python
state["metadata"]["scenario_name"] = scenario_name
state["metadata"]["goal"] = conversation_config.goal
```

## Testing Results

**All Tests Passing**: 26/26 tests successful

Key tests confirm:
- Legacy `conversation` format works
- New `conversations` format works
- Agent filtering operates correctly
- Template context includes scenario info
- API endpoints return proper data

## Example Use Cases

### Use Case 1: Research vs. Debate
Define separate scenarios for:
- **Research Mode**: Researcher + Analyst explore topics systematically
- **Debate Mode**: Optimist + Realist discuss pros/cons

### Use Case 2: Different Depths
- **Quick Check**: Short responses, 5 cycles
- **Deep Dive**: Long responses, 20 cycles
- **Expert Panel**: All agents, comprehensive discussion

### Use Case 3: Role-Specific Scenarios
- **Technical Review**: Engineers only
- **Business Review**: Analysts and strategists
- **User Feedback**: UX experts and product managers

## API Examples

### List Available Scenarios

**Request**
```http
GET http://localhost:8000/api/conversation/scenarios
```

**Response**
```json
{
  "scenarios": [
    {
      "name": "Research and Synthesis",
      "goal": "Explore topic through research and analysis",
      "brevity": "medium",
      "max_cycles": 10,
      "starting_agent": "researcher",
      "agents_involved": ["researcher", "analyst"]
    },
    {
      "name": "Opposites Debate",
      "goal": "Debate different perspectives",
      "brevity": "short",
      "max_cycles": 12,
      "starting_agent": "optimist",
      "agents_involved": ["optimist", "realist"]
    }
  ],
  "default": "Research and Synthesis"
}
```

### Start with Scenario

**Request**
```http
POST http://localhost:8000/api/conversation/start?scenario=Opposites%20Debate
```

**Response**
```json
{
  "status": "started",
  "scenario": "Opposites Debate",
  "conversation_id": "abc-123",
  "started_at": "2024-01-15T10:30:00Z",
  "agents": ["optimist", "realist"],
  "max_cycles": 12
}
```

## Configuration Validation

The validator ensures:

1. **Unique names**: No duplicate scenario names
2. **Valid agents**: Starting agent and agents_involved exist
3. **Consistent filtering**: Starting agent in agents_involved if specified
4. **Required fields**: All scenarios have name, goal, brevity
5. **At least one scenario**: Either conversation or non-empty conversations

## Benefits

### For Users
- **Flexibility**: Multiple scenarios in one config
- **Reusability**: Same agents, different conversations
- **Organization**: Clear separation of use cases
- **Efficiency**: No need to swap config files

### For Developers
- **Clean architecture**: Scenario as first-class concept
- **Template power**: Rich context for customization
- **Extensibility**: Easy to add scenario-specific features
- **Backward compatible**: No breaking changes

## Future Enhancements

### Potential Additions
1. **Scenario templates**: Predefined scenario types
2. **Scenario chaining**: Run multiple scenarios in sequence
3. **Conditional routing**: Dynamic scenario selection based on content
4. **Scenario history**: Track which scenarios were run
5. **Scenario comparison**: Compare outcomes across scenarios

### Advanced Features
- **Dynamic scenarios**: Generate scenarios from conversation content
- **Scenario branching**: Fork conversation into different scenarios
- **Scenario metrics**: Performance tracking per scenario
- **Scenario recommendations**: Suggest best scenario for user goal

## Migration Guide

### Converting Single to Multiple Scenarios

**Before (Legacy)**
```yaml
conversation:
  starting_agent: "agent_a"
  max_cycles: 5
```

**After (Multi-Scenario)**
```yaml
conversations:
  - name: "Default Conversation"
    goal: "General discussion"
    brevity: "medium"
    starting_agent: "agent_a"
    max_cycles: 5
```

**Incremental Migration**: Both formats work, so users can migrate at their own pace.

## Lessons Learned

1. **Backward compatibility is crucial**: Preserving existing functionality prevented disruption
2. **hasattr checks**: Necessary for checking optional fields on Pydantic models
3. **Template context**: Rich context enables powerful customization
4. **State tracking**: Including scenario in metadata aids debugging and analytics
5. **Agent filtering**: Requires careful handling in routing logic

## Conclusion

Phase 6 successfully adds multi-scenario support while maintaining full backward compatibility. The implementation is clean, well-tested, and provides immediate value for users who need to manage multiple conversation types.

The feature aligns with the project's goal of providing a flexible, powerful platform for multi-agent conversations. By making scenarios a first-class concept, we enable more sophisticated use cases while keeping the configuration simple and intuitive.

## Next Steps

1. **User feedback**: Gather feedback on scenario feature
2. **Documentation updates**: Add examples to main README
3. **Example scenarios**: Create more example configurations
4. **Tutorial video**: Demonstrate scenario switching in UI
5. **Community examples**: Encourage users to share scenario configs
