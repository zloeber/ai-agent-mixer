# Fix for Conversation Start Issue

## Problem
After clicking the 'Start' button for a conversation, there were no visible errors, logs, or conversation output, and the cycle count did not update on the frontend. Backend logs showed the conversation was started but nothing progressed.

## Root Causes

### 1. Backend Graph Routing Bug
The orchestrator was using `self.config.agents` instead of `active_agents` when setting up graph routing. This caused routing failures when:
- Using multi-scenario configurations
- Some agents were inactive in certain scenarios

**Files affected:**
- `backend/app/core/orchestrator.py` (lines 186, 208)

### 2. Missing Error Broadcasting
When errors occurred (e.g., Ollama not running), they were:
- Logged on the backend
- Added to conversation state
- But NOT broadcast to the frontend via WebSocket

This caused silent failures from the user's perspective.

**Files affected:**
- `backend/app/agents/agent_node.py` (error handlers)

### 3. No User-Visible Errors
Even if errors had been broadcast, the frontend was only logging them to console, not displaying them to users.

**Files affected:**
- `frontend/src/components/ConversationExchange.tsx`
- `frontend/src/components/ControlPanel.tsx`

## Solution Implemented

### Backend Changes

#### 1. Fixed Graph Routing (orchestrator.py)
```python
# Before (WRONG):
**{agent_id: agent_id for agent_id in self.config.agents.keys()}

# After (CORRECT):
**{agent_id: agent_id for agent_id in active_agents.keys()}
```

This ensures routing only includes agents that are active in the current scenario.

#### 2. Added Error Broadcasting (agent_node.py)
Added WebSocket broadcasts for all error types:
- `OllamaConnectionError` → broadcasts with type "ollama_connection"
- `AgentTimeoutError` → broadcasts with type "timeout"
- `Exception` → broadcasts with type "unexpected"

Each error broadcast includes:
- `error`: Human-readable error message
- `agent_id`: Which agent encountered the error
- `error_type`: Category of error for frontend handling

#### 3. Enhanced Logging (orchestrator.py)
Added comprehensive logging:
- INFO level: Execution start/completion, cycle registration
- DEBUG level: Per-event logging for troubleshooting
- Event counters to track graph execution progress

### Frontend Changes

#### 1. Created Error Handling Utility (utils/errorHandling.ts)
New centralized utility for displaying errors:
```typescript
interface ConversationError {
  error: string;
  agent_id?: string;
  error_type?: 'ollama_connection' | 'timeout' | 'unexpected';
}

function displayConversationError(errorData: string | ConversationError): void
```

Benefits:
- Type-safe error handling
- Single source of truth for error messages
- Easy to upgrade to toast system later (see TODO)

#### 2. Updated Components
Both `ConversationExchange.tsx` and `ControlPanel.tsx` now:
- Import and use `displayConversationError`
- Show user-friendly error messages with helpful context
- Suggest checking Ollama status

## Testing

### Test Script Created
Created `/tmp/test_conversation_flow.py` to test:
- ✅ Successful conversation execution with mocked Ollama
- ✅ Error handling when Ollama is unavailable
- ✅ Graph execution flow and event streaming

### Test Results
- All existing unit tests pass (26/26)
- Graph execution works correctly with active agents
- Errors are properly caught and broadcast
- Frontend receives and displays errors

### Security
- CodeQL scan: 0 alerts found
- No new vulnerabilities introduced

## Expected Behavior After Fix

### When Ollama is NOT Available:
1. User clicks "Start" button
2. Backend starts conversation, broadcasts `conversation_started`
3. Frontend auto-continues conversation (calls `/api/conversation/continue`)
4. Backend attempts to call Ollama → **CONNECTION ERROR**
5. Backend logs error, adds error message to state
6. Backend broadcasts `conversation_error` via WebSocket
7. **Frontend displays alert**: "Conversation Error: Connection refused: Ollama is not running. Please check that Ollama is running..."
8. Conversation terminates with status "Completed"

### When Ollama IS Available:
1. User clicks "Start" button
2. Backend starts conversation, broadcasts `conversation_started`
3. Frontend auto-continues conversation
4. Backend successfully calls Ollama for agent responses
5. Messages appear in conversation exchange in real-time
6. Cycle count updates correctly
7. Agents take turns until max_cycles or termination condition

## Files Changed

### Backend (Python)
- `backend/app/core/orchestrator.py`: Fixed routing, added logging
- `backend/app/agents/agent_node.py`: Added error broadcasting

### Frontend (TypeScript/React)
- `frontend/src/utils/errorHandling.ts`: New error handling utility (CREATED)
- `frontend/src/components/ConversationExchange.tsx`: Uses error utility
- `frontend/src/components/ControlPanel.tsx`: Uses error utility

## Future Improvements

1. **Replace `alert()` with toast notifications**: The current implementation uses browser alerts for simplicity. Should be replaced with a proper toast/notification system for better UX.

2. **More specific error messages**: Use the `error_type` field to provide more tailored messages and recovery suggestions.

3. **Error recovery actions**: Add "Retry" buttons or automatic reconnection logic.

4. **Better Ollama status checking**: Check Ollama availability before starting conversation.

## How to Test the Fix

### Prerequisites
- Ollama installed and running (or intentionally stopped to test error handling)
- Example config loaded (e.g., `config/example-simple.yaml`)

### Test Case 1: Error Handling (Ollama Stopped)
1. **Stop Ollama**: `pkill ollama` or stop the service
2. **Load config**: Upload `example-simple.yaml` in UI
3. **Start conversation**: Click "Start" button
4. **Expected result**: 
   - Alert displays: "Conversation Error: ..."
   - Status shows "Completed"
   - Backend logs show OllamaConnectionError
   - Frontend console shows error details

### Test Case 2: Successful Execution (Ollama Running)
1. **Start Ollama**: `ollama serve`
2. **Ensure models available**: `ollama pull llama2`
3. **Load config**: Upload `example-simple.yaml` in UI
4. **Start conversation**: Click "Start" button
5. **Expected result**:
   - Messages appear in conversation exchange
   - Cycle count increments (0 → 1 → 2...)
   - Agent responses stream in real-time
   - Conversation completes normally

## Summary

This fix ensures users always get clear feedback about what's happening with their conversations. Silent failures are eliminated through comprehensive error broadcasting and user-visible error messages. The graph routing bug is fixed to support multi-scenario configurations properly. Enhanced logging helps with troubleshooting any future issues.
