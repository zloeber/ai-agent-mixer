# Testing Guide for Conversation Start and Agent Configuration UI

This document provides a comprehensive testing guide for the changes made to fix conversation start issues and add agent configuration UI.

## Overview of Changes

### 1. Runtime Configuration Overrides
- **Feature**: Max cycles and starting agent can now be overridden at runtime
- **Location**: Control Panel → Max Cycles input and Starting Agent dropdown
- **Backend API**: `/api/conversation/start?max_cycles=X&starting_agent=Y`

### 2. Fixed Endless "Running..." State
- **Issue**: After starting a conversation, the UI would show "Running..." endlessly
- **Fix**: Improved error handling, better state management, increased auto-continue delay
- **Verification**: Start a conversation and verify it completes without getting stuck

### 3. Agent Configuration UI
- **Feature**: Tabbed interface for each agent (Console/Config)
- **Location**: Left and right panels (Agent A and Agent B)
- **Capabilities**: 
  - Console tab: View agent thoughts and internal reasoning
  - Config tab: Edit agent configuration
  - Download button: Export YAML with changes

## Test Plan

### Prerequisites
1. Have Ollama running with at least one model available
2. Start the backend: `cd backend && uvicorn app.main:app --reload`
3. Start the frontend: `cd frontend && npm run dev`
4. Open browser to `http://localhost:5173`

### Test 1: Load Configuration
**Steps:**
1. In Configuration Editor panel (bottom), click "📁 Load File"
2. Select a YAML configuration file (e.g., `config/example-simple.yaml`)
3. Click "✓ Validate" to validate the configuration
4. Click "⚡ Apply" to load the configuration

**Expected Result:**
- Configuration loads successfully
- Green "✓ Valid" indicator appears
- Control Panel shows available agents in Starting Agent dropdown

### Test 2: Runtime Override - Max Cycles
**Steps:**
1. Load a configuration with `max_cycles: 5`
2. In Control Panel, change Max Cycles to `3`
3. Click "▶️ Start" button
4. Monitor the "Cycle: X / Y" indicator in Control Panel

**Expected Result:**
- Conversation starts successfully
- Cycle indicator shows "Cycle: 0 / 3" (not 5)
- Conversation terminates after 3 cycles
- "✓ Conversation Complete" appears in Conversation Exchange header

### Test 3: Runtime Override - Starting Agent
**Steps:**
1. Load a configuration with `starting_agent: agent_a`
2. In Control Panel, change Starting Agent to `agent_b`
3. Click "▶️ Start" button
4. Check Conversation Exchange for first message

**Expected Result:**
- Conversation starts with Agent B speaking first
- First message in exchange is from Agent B

### Test 4: No Endless "Running..." State
**Steps:**
1. Load a valid configuration
2. Click "▶️ Start" button
3. Monitor the "Running..." indicator in Conversation Exchange header
4. Wait for first cycle to complete

**Expected Result:**
- "Running..." appears briefly (< 1 second)
- First message appears in Conversation Exchange
- "Running..." disappears after message is received
- No errors in browser console

### Test 5: Agent Configuration - View
**Steps:**
1. Load a configuration
2. Click "⚙️ Config" tab in Agent A panel (left side)
3. Review displayed configuration

**Expected Result:**
- Configuration loads successfully
- All fields display current values:
  - Agent Name
  - Persona (system prompt)
  - Provider, API URL, Model Name
  - Thinking Mode checkbox
  - Temperature slider (with value)
  - Top P slider (with value)
  - MCP Servers list

### Test 6: Agent Configuration - Edit
**Steps:**
1. Click "⚙️ Config" tab in Agent A panel
2. Change Agent Name from "Agent A" to "Alice"
3. Modify Persona text
4. Adjust Temperature slider to 0.5
5. Adjust Top P slider to 0.8

**Expected Result:**
- All changes are immediately visible
- No errors in browser console
- Changes are tracked (hasChanges state = true)

### Test 7: Download with Changes
**Steps:**
1. Follow Test 6 to make agent configuration changes
2. Also make changes to Agent B (click Config tab, edit name to "Bob")
3. In Configuration Editor (bottom), observe the animated "⬇️ Download w/ Changes" button
4. Click "⬇️ Download w/ Changes" button
5. Open downloaded YAML file

**Expected Result:**
- "⬇️ Download w/ Changes" button appears (with pulse animation)
- YAML file downloads with timestamp in filename
- Downloaded YAML contains updated agent names:
  ```yaml
  agents:
    agent_a:
      name: "Alice"
      # ... other fields
    agent_b:
      name: "Bob"
      # ... other fields
  ```
- All other changes (persona, temperature, etc.) are also reflected

### Test 8: Configuration Validation
**Steps:**
1. Make agent configuration changes
2. Click "⬇️ Download w/ Changes"
3. In Configuration Editor, click "📁 Load File"
4. Select the downloaded YAML file
5. Click "✓ Validate"
6. Click "⚡ Apply"

**Expected Result:**
- Validation passes (green "✓ Valid")
- Configuration loads successfully
- Agent Config tabs show updated values

### Test 9: Multiple Cycle Execution
**Steps:**
1. Load configuration and start conversation
2. After first cycle completes, click "+5" button in Conversation Exchange
3. Monitor cycle progress
4. Click "+10" button to run more cycles
5. Click "▶️ All" button to run to completion

**Expected Result:**
- Each button executes the specified number of cycles
- Cycle counter updates correctly
- "Running..." appears and disappears appropriately
- Progress bar in Control Panel updates
- Conversation terminates at max_cycles

### Test 10: Agent Console Tab
**Steps:**
1. Load configuration with `thinking: true` in agent model config
2. Start conversation
3. Click "📊 Console" tab in Agent A panel
4. Watch for thought messages

**Expected Result:**
- Console tab displays thoughts/internal reasoning from Agent A
- Thoughts appear in green text with timestamps
- Thoughts are separate from conversation messages
- Console auto-scrolls to bottom

### Test 11: Mark as Applied / Reset
**Steps:**
1. Make agent configuration changes
2. Click "✓ Mark as Applied" button
3. Observe UI changes
4. Make more changes
5. Click "↺ Reset" button

**Expected Result:**
- After "Mark as Applied": hasChanges indicator clears, but changes remain in form
- After "Reset": form reloads from backend, changes are discarded
- Download button appears/disappears based on changes

### Test 12: Error Handling
**Steps:**
1. Stop Ollama or make model URL invalid
2. Load configuration and start conversation
3. Observe error handling

**Expected Result:**
- Error alert appears with meaningful message
- "Running..." state clears
- Console shows detailed error
- User can try again after fixing issue

## Browser Console Checks

During testing, monitor the browser console for:
1. ✅ No unexpected errors
2. ✅ Clear log messages for major actions:
   - "Conversation started: ..."
   - "Auto-continuing conversation for 1 cycle..."
   - "Auto-continued conversation: ..."
   - "Running X cycle(s)..."
   - "Completed Y cycles, now at cycle Z"

## Backend Logs

Monitor backend logs for:
1. ✅ Configuration override logging:
   ```
   INFO: Overriding max_cycles: 5 -> 3
   INFO: Overriding starting_agent: agent_a -> agent_b
   ```
2. ✅ Agent validation warnings if applicable
3. ✅ No unexpected errors during conversation execution

## Known Limitations

1. **MCP Servers**: The Config tab displays MCP servers but doesn't allow editing them yet
2. **Agent Metadata**: Custom metadata fields are not exposed in the UI yet
3. **Model Parameters**: Only temperature and top_p are exposed; other parameters require YAML editing
4. **Multi-Agent**: UI is optimized for 2-agent conversations (agent_a, agent_b)

## Troubleshooting

### Issue: Configuration won't load
- **Solution**: Check YAML syntax is valid, check browser console for errors

### Issue: "Running..." never clears
- **Solution**: Check browser console for error messages, verify Ollama is accessible

### Issue: Download button doesn't appear
- **Solution**: Make sure you've made changes in Config tab, check agentConfigChanges state

### Issue: Changes not reflected in download
- **Solution**: Verify you clicked Download w/ Changes (not Export), check downloaded file content

## Success Criteria

All tests should pass with:
- ✅ No browser console errors
- ✅ No backend errors in logs
- ✅ UI behaves as expected
- ✅ Configuration changes persist in downloads
- ✅ Conversations execute without hanging
- ✅ Cycle counts match configured/overridden values
