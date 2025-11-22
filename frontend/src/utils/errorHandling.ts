/**
 * Utility functions for error handling and user notifications
 */

/**
 * Error object structure from backend
 */
interface ConversationError {
  error: string;
  agent_id?: string;
  error_type?: 'ollama_connection' | 'timeout' | 'unexpected';
}

/**
 * Display a conversation error to the user with helpful context
 * @param errorData Error message or object from the backend
 */
export function displayConversationError(errorData: string | ConversationError): void {
  let errorMessage: string;
  
  if (typeof errorData === 'string') {
    errorMessage = errorData;
  } else {
    errorMessage = errorData.error || 'Unknown error occurred';
    // Could use agent_id and error_type for more specific messaging in the future
  }
  
  // For now, use alert() as a minimal solution
  // TODO: Replace with a proper toast/notification system
  alert(
    `Conversation Error: ${errorMessage}\n\n` +
    'Please check that Ollama is running and the configured models are available.'
  );
}
