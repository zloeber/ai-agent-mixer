# Phase 6 Quick Start: Multi-Scenario Configuration

## What's New?

You can now define multiple conversation scenarios in a single configuration file and switch between them in the UI!

## Quick Example

### 1. Create Configuration with Multiple Scenarios

Create `config/my-scenarios.yaml`:

```yaml
version: "1.0"

agents:
  researcher:
    name: "Research Assistant"
    persona: "Academic researcher"
    model:
      url: "http://localhost:11434"
      model_name: "llama3.2:latest"
  
  analyst:
    name: "Business Analyst"
    persona: "Strategic thinker"
    model:
      url: "http://localhost:11434"
      model_name: "mistral:latest"

conversations:
  - name: "Deep Research"
    goal: "Systematic research and analysis"
    brevity: "medium"
    max_cycles: 10
    agents_involved: [researcher, analyst]
  
  - name: "Quick Analysis"
    goal: "Fast strategic overview"
    brevity: "short"
    max_cycles: 5
    agents_involved: [analyst]

initialization:
  first_message: "What are the implications of AI in education?"
  system_prompt_template: |
    You are {{ agent.name }}.
    Scenario: {{ conversation.scenario_name }}
    Goal: {{ conversation.goal }}
    Keep responses {{ conversation.brevity }}.

logging:
  level: "INFO"
```

### 2. Load Configuration

```bash
# Upload via UI at http://localhost:3000
# Or save to config/ directory
```

### 3. Start Backend

```bash
docker-compose up -d
# or
task docker:up
```

### 4. Select Scenario in UI

1. Open http://localhost:3000
2. Configuration Panel > Upload `my-scenarios.yaml`
3. Control Panel > **Scenario dropdown** appears
4. Select "Deep Research" or "Quick Analysis"
5. Click ▶️ Start

### 5. Watch It Run!

The conversation will use the selected scenario's:
- Goal and context
- Agent filtering
- Brevity settings
- Max cycles

## API Usage

### List Scenarios

```bash
curl http://localhost:8000/api/conversation/scenarios
```

### Start with Scenario

```bash
curl -X POST "http://localhost:8000/api/conversation/start?scenario=Deep%20Research"
```

## Key Features

✅ **Multiple scenarios per config**
✅ **Agent filtering per scenario**
✅ **Different goals and settings**
✅ **UI scenario selector**
✅ **Template context variables**
✅ **Backward compatible**

## Template Variables

Available in `system_prompt_template`:

```jinja2
{{ conversation.scenario_name }}     # "Deep Research"
{{ conversation.goal }}               # "Systematic research..."
{{ conversation.brevity }}            # "medium"
{{ conversation.max_cycles }}         # 10
{{ conversation.agents_involved }}    # ["researcher", "analyst"]
```

## Common Scenarios

### Research Mode
```yaml
- name: "Research Mode"
  goal: "Thorough investigation and analysis"
  brevity: "long"
  max_cycles: 15
  agents_involved: [researcher, analyst]
```

### Quick Debate
```yaml
- name: "Quick Debate"
  goal: "Fast exploration of pros and cons"
  brevity: "short"
  max_cycles: 6
  agents_involved: [optimist, critic]
```

### All-Hands Discussion
```yaml
- name: "All-Hands"
  goal: "Comprehensive multi-perspective discussion"
  brevity: "medium"
  max_cycles: 20
  # No agents_involved = all agents participate
```

## Migration from Legacy

### Old Format (Still Works!)
```yaml
conversation:
  starting_agent: "agent_a"
  max_cycles: 5
```

### New Format
```yaml
conversations:
  - name: "Default"
    goal: "General discussion"
    brevity: "medium"
    starting_agent: "agent_a"
    max_cycles: 5
```

Both formats work. Use whichever suits your needs!

## Examples

See `config/multi-scenario-example.yaml` for a complete example with:
- 4 agents (researcher, analyst, optimist, realist)
- 3 scenarios (Research, Debate, Roundtable)
- Rich template usage
- Agent metadata integration

## Troubleshooting

**Scenario dropdown not appearing?**
- Check configuration is loaded (health endpoint)
- Verify YAML is valid
- Ensure at least one scenario is defined

**Wrong agents in conversation?**
- Check `agents_involved` list
- Verify agent IDs match `agents` section
- Confirm `starting_agent` is in `agents_involved`

**Template variables not working?**
- Use Jinja2 syntax: `{{ variable }}`
- Check spelling of variable names
- Ensure template is in `system_prompt_template`

## What's Next?

1. **Experiment**: Try different scenario combinations
2. **Share**: Post your scenarios in GitHub Discussions
3. **Customize**: Use template variables creatively
4. **Iterate**: Refine scenarios based on results

## More Info

- Full guide: `docs/MULTI_SCENARIO.md`
- Complete summary: `docs/PHASE6_SUMMARY.md`
- Example config: `config/multi-scenario-example.yaml`

---

Happy scenario building! 🎭
