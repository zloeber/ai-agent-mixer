# Agent Metadata Feature

## Overview

Agent metadata allows you to define custom attributes for each agent that can be referenced in initialization prompts using Jinja2 templates. This enables more dynamic and flexible agent configuration without modifying code.

## Configuration

### Adding Metadata to Agents

In your YAML configuration file, add a `metadata` dictionary to any agent:

```yaml
agents:
  researcher:
    name: "Lead Researcher"
    persona: |
      You are a meticulous researcher...
    model:
      provider: "ollama"
      url: "http://localhost:11434"
      model_name: "llama2"
    metadata:
      expertise: "academic research"
      focus_area: "data collection"
      priority: "accuracy"
      years_experience: 10
      specialty: ["qualitative analysis", "literature review"]
```

The metadata dictionary can contain any JSON-serializable values:
- Strings
- Numbers
- Booleans
- Lists
- Nested dictionaries

## Using Metadata in Templates

### Basic Template Usage

In the `initialization.system_prompt_template`, access metadata via `agent.metadata`:

```yaml
initialization:
  system_prompt_template: |
    You are {{ agent.name }}.
    
    Your expertise: {{ agent.metadata.expertise }}
    Your focus: {{ agent.metadata.focus_area }}
    Priority: {{ agent.metadata.priority }}
    
    {{ agent.persona }}
```

### Conditional Logic

Use Jinja2 conditionals to handle optional metadata:

```yaml
initialization:
  system_prompt_template: |
    You are {{ agent.name }}.
    
    {% if agent.metadata.expertise %}
    Area of Expertise: {{ agent.metadata.expertise }}
    {% endif %}
    
    {% if agent.metadata.years_experience %}
    Experience Level: {{ agent.metadata.years_experience }} years
    {% endif %}
    
    {{ agent.persona }}
```

### Iterating Over Lists

Process list values in metadata:

```yaml
initialization:
  system_prompt_template: |
    You are {{ agent.name }}.
    
    {% if agent.metadata.specialty %}
    Your specialties include:
    {% for spec in agent.metadata.specialty %}
    - {{ spec }}
    {% endfor %}
    {% endif %}
    
    {{ agent.persona }}
```

### Accessing Nested Values

Handle nested metadata structures:

```yaml
agents:
  analyst:
    name: "Data Analyst"
    persona: "You analyze data..."
    metadata:
      skills:
        primary: "statistical analysis"
        secondary: "data visualization"
      certifications:
        - "Data Science Professional"
        - "Advanced Analytics"

# In template:
initialization:
  system_prompt_template: |
    Primary skill: {{ agent.metadata.skills.primary }}
    Secondary skill: {{ agent.metadata.skills.secondary }}
    
    Certifications:
    {% for cert in agent.metadata.certifications %}
    - {{ cert }}
    {% endfor %}
```

## Complete Example

See `config/example-with-metadata.yaml` for a full working example that demonstrates:
- Multiple agents with different metadata
- Template-based prompt generation
- Using metadata to create distinct agent personalities
- Conditional rendering based on metadata presence

## Use Cases

### 1. Personality Traits
```yaml
metadata:
  personality_trait: "optimistic"
  communication_style: "encouraging"
  favorite_quote: "Every cloud has a silver lining"
```

### 2. Technical Expertise
```yaml
metadata:
  expertise: "machine learning"
  languages: ["Python", "R", "Julia"]
  frameworks: ["PyTorch", "TensorFlow"]
```

### 3. Role-Specific Context
```yaml
metadata:
  department: "Research & Development"
  clearance_level: "senior"
  reporting_to: "CTO"
```

### 4. Dynamic Behavior Flags
```yaml
metadata:
  verbose: true
  use_examples: true
  citation_style: "APA"
  max_response_length: 500
```

## Template Context Reference

The following variables are available in templates:

- `agent.name` - Agent display name
- `agent.persona` - Agent persona text
- `agent.model` - Model name
- `agent.metadata` - Full metadata dictionary
- `conversation.max_cycles` - Maximum conversation cycles
- `conversation.starting_agent` - Starting agent ID
- `tools` - List of available tools (if MCP servers configured)
- `has_tools` - Boolean indicating tool availability

## Best Practices

1. **Keep metadata flat when possible** - Easier to reference in templates
2. **Use consistent keys** - Define a standard set of metadata keys across agents
3. **Provide defaults in templates** - Use Jinja2 conditionals to handle missing keys
4. **Document your metadata schema** - Comment your YAML files to explain custom keys
5. **Test templates thoroughly** - Validate that all metadata paths resolve correctly

## Schema Definition

The metadata field is defined in `backend/app/schemas/config.py`:

```python
class AgentConfig(BaseModel):
    name: str
    persona: str
    model: ModelConfig
    mcp_servers: List[str] = []
    metadata: Dict[str, Any] = {}  # Custom metadata attributes
```

## Implementation Details

- Metadata is passed to the `PromptBuilder` service
- Templates are rendered using Jinja2
- All metadata is included in the template context as `agent.metadata`
- Empty metadata dictionaries are valid (no metadata required)
- Metadata does not affect agent behavior directly - only how prompts are constructed

## Migration Guide

Existing configurations without metadata will continue to work:
- `metadata` field defaults to empty dictionary
- Templates can check for metadata existence before using it
- No breaking changes to existing configs

To add metadata to existing agents:
1. Add `metadata: {}` to agent config
2. Define custom key-value pairs
3. Update system prompt template to use metadata
4. Test prompt generation
