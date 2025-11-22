/**
 * Utility functions for error handling and user notifications
 */

/**
 * Display a conversation error to the user with helpful context
 * @param error Error message or object from the backend
 */
export function displayConversationError(error: string | { error?: string }): void {
  const errorMessage = typeof error === 'string' ? error : (error.error || 'Unknown error occurred');
  
  // For now, use alert() as a minimal solution
  // TODO: Replace with a proper toast/notification system
  alert(
    `Conversation Error: ${errorMessage}\n\n` +
    'Please check that Ollama is running and the configured models are available.'
  );
}
