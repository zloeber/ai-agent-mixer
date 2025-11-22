# Troubleshooting Guide

## Common Issues and Solutions

### Excessive Ellipsis Output

**Symptom**: Agents produce output filled with ellipsis characters (`…`, `....`, "Scrolling…"):
```
……………………………………….………………………………………….…………….………
…………
……….………….….………………………………………
Scrolling………………
```

**Cause**: When models have `thinking: true` enabled, they may output ellipsis as part of their internal reasoning process. The thinking suppression callback filters these out, but sometimes excessive ellipsis can leak through.

**Solutions**:

1. **Disable thinking mode** (quickest fix):
   ```yaml
   agents:
     agent_name:
       model:
         thinking: false  # Disable internal reasoning display
   ```

2. **Use a different model**: Some models are more prone to ellipsis output. Try:
   - `mistral:latest` - Generally cleaner output
   - `llama2` - Good balance
   - Avoid models known for verbose thinking patterns

3. **Update prompt instructions**: Add explicit guidance in your system prompt:
   ```yaml
   initialization:
     system_prompt_template: |
       ...
       ## Response Guidelines
       - Provide clear, substantive responses
       - Avoid using excessive ellipsis (...) or placeholder text
       - Be direct and articulate your thoughts completely
       - Do not output filler characters or scrolling indicators
   ```

4. **The system already filters**: As of the latest update, the system automatically:
   - Detects and filters ellipsis patterns in real-time
   - Removes excessive punctuation in post-processing
   - Skips messages that are only punctuation/whitespace
   - Treats long ellipsis sequences as internal thinking

### Empty or Missing Responses

**Symptom**: Agents don't respond or produce very short/empty messages.

**Cause**: 
- Response was entirely ellipsis/thinking and got filtered out
- Model timeout
- Connection issues with Ollama

**Solutions**:

1. **Check Ollama connection**:
   ```bash
   curl http://your-ollama-url:11434/api/tags
   ```

2. **Increase timeout**:
   ```yaml
   conversation:
     turn_timeout: 600  # 10 minutes
   ```

3. **Check logs** for error messages:
   ```bash
   tail -f backend/logs/app.log
   ```

4. **Try a more reliable model**:
   ```yaml
   model:
     model_name: "mistral:latest"
     thinking: false
   ```

### Agents Not Taking Turns

**Symptom**: One agent dominates or conversation stops unexpectedly.

**Cause**: 
- Cycle counting issue
- Termination conditions triggered
- One agent producing invalid output

**Solutions**:

1. **Check max_cycles setting**:
   ```yaml
   conversation:
     max_cycles: 20  # Increase if needed
   ```

2. **Review termination conditions**:
   ```yaml
   conversation:
     termination_conditions:
       keyword_triggers: []  # Remove if too aggressive
       silence_detection: 10  # Increase threshold
   ```

3. **Monitor cycle progress**: The UI shows current cycle count

### WebSocket Connection Issues

**Symptom**: UI shows "Disconnected", messages don't appear in real-time.

**Solutions**:

1. **Restart backend**:
   ```bash
   cd backend
   uv run uvicorn app.main:app --reload
   ```

2. **Check CORS settings** in `backend/app/main.py`

3. **Verify WebSocket URL** in frontend `.env`:
   ```
   VITE_WS_URL=ws://localhost:8000
   ```

### Configuration Validation Errors

**Symptom**: Config file won't load, validation errors.

**Solutions**:

1. **Validate YAML syntax**:
   ```bash
   python -c "import yaml; yaml.safe_load(open('config/your-config.yaml'))"
   ```

2. **Check required fields**:
   - `version`
   - `conversation.starting_agent`
   - `agents` (minimum 2)
   - `initialization.first_message`

3. **Use example configs as templates**: See `config/example-*.yaml`

## Debug Mode

Enable detailed logging:

```yaml
logging:
  level: "DEBUG"
  include_thoughts: true
  output_directory: "./logs"
```

Then check logs:
```bash
tail -f backend/logs/app.log | grep ERROR
```

## Getting Help

1. Check logs in `backend/logs/`
2. Review configuration against examples
3. Test with minimal config first
4. Verify Ollama is running and models are downloaded
5. Check GitHub issues for similar problems
