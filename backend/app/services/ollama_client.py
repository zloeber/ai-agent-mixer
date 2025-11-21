"""Ollama client service for connecting to and interacting with Ollama instances."""

import asyncio
import logging
from typing import Any, AsyncIterator, Callable, Dict, List, Optional

import httpx
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage
from langchain_ollama import ChatOllama

from ..schemas.config import ModelConfig

logger = logging.getLogger(__name__)


class OllamaConnectionError(Exception):
    """Exception raised when connection to Ollama fails."""
    pass


class OllamaModelNotFoundError(Exception):
    """Exception raised when requested model is not available."""
    pass


class OllamaClient:
    """Client for interacting with Ollama instances."""
    
    def __init__(self, config: ModelConfig):
        """
        Initialize Ollama client with model configuration.
        
        Args:
            config: Model configuration including URL, model name, and parameters
        """
        self.config = config
        self.url = config.url.rstrip('/')
        self.model_name = config.model_name
        self.parameters = config.parameters or {}
        self._client: Optional[ChatOllama] = None
        self._http_client: Optional[httpx.AsyncClient] = None
        
    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client for connection testing."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=30.0)
        return self._http_client
        
    async def verify_connection(self) -> bool:
        """
        Verify connection to Ollama server and model availability.
        
        Returns:
            True if connection and model are available
            
        Raises:
            OllamaConnectionError: If server is unreachable
            OllamaModelNotFoundError: If model is not found
        """
        try:
            client = await self._get_http_client()
            
            # Test server connectivity
            try:
                response = await client.get(f"{self.url}/api/tags")
                response.raise_for_status()
            except httpx.HTTPError as e:
                raise OllamaConnectionError(
                    f"Failed to connect to Ollama at {self.url}: {str(e)}"
                )
            
            # Check if model is available
            models_data = response.json()
            available_models = [m.get("name", "") for m in models_data.get("models", [])]
            
            # Handle both full model names and base names
            model_available = any(
                self.model_name in model or model.startswith(self.model_name)
                for model in available_models
            )
            
            if not model_available:
                raise OllamaModelNotFoundError(
                    f"Model '{self.model_name}' not found. Available models: {available_models}"
                )
            
            logger.info(f"Successfully verified connection to {self.url} with model {self.model_name}")
            return True
            
        except (OllamaConnectionError, OllamaModelNotFoundError):
            raise
        except Exception as e:
            raise OllamaConnectionError(f"Unexpected error verifying connection: {str(e)}")
    
    def _get_client(self) -> ChatOllama:
        """Get or create LangChain Ollama client."""
        if self._client is None:
            # Extract temperature and other common parameters
            temperature = self.parameters.get("temperature", 0.7)
            top_p = self.parameters.get("top_p", 0.9)
            
            # Build kwargs for ChatOllama
            kwargs: Dict[str, Any] = {
                "model": self.model_name,
                "base_url": self.url,
                "temperature": temperature,
            }
            
            # Add top_p if specified
            if "top_p" in self.parameters:
                kwargs["top_p"] = top_p
            
            # Add any other parameters that ChatOllama supports
            for key in ["num_predict", "top_k", "repeat_penalty"]:
                if key in self.parameters:
                    kwargs[key] = self.parameters[key]
            
            self._client = ChatOllama(**kwargs)
            logger.debug(f"Created ChatOllama client for {self.model_name} at {self.url}")
        
        return self._client
    
    async def generate_response(
        self,
        messages: List[BaseMessage],
        stream: bool = False,
        callbacks: Optional[List[Any]] = None
    ) -> AIMessage:
        """
        Generate a response from the model.
        
        Args:
            messages: List of conversation messages
            stream: Whether to stream the response
            callbacks: Optional list of callback handlers
            
        Returns:
            AIMessage with the model's response
            
        Raises:
            OllamaConnectionError: If generation fails
        """
        try:
            client = self._get_client()
            
            # Configure callbacks if provided
            config = {}
            if callbacks:
                config["callbacks"] = callbacks
            
            if stream:
                # For streaming, we'll collect the response
                full_response = ""
                async for chunk in client.astream(messages, config=config):
                    if hasattr(chunk, "content"):
                        full_response += chunk.content
                return AIMessage(content=full_response)
            else:
                # Non-streaming generation
                response = await client.ainvoke(messages, config=config)
                return response
                
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            raise OllamaConnectionError(f"Failed to generate response: {str(e)}")
    
    async def stream_response(
        self,
        messages: List[BaseMessage],
        callbacks: Optional[List[Any]] = None
    ) -> AsyncIterator[str]:
        """
        Stream response tokens from the model.
        
        Args:
            messages: List of conversation messages
            callbacks: Optional list of callback handlers
            
        Yields:
            Response tokens as they are generated
            
        Raises:
            OllamaConnectionError: If streaming fails
        """
        try:
            client = self._get_client()
            
            # Configure callbacks if provided
            config = {}
            if callbacks:
                config["callbacks"] = callbacks
            
            async for chunk in client.astream(messages, config=config):
                if hasattr(chunk, "content") and chunk.content:
                    yield chunk.content
                    
        except Exception as e:
            logger.error(f"Error streaming response: {str(e)}")
            raise OllamaConnectionError(f"Failed to stream response: {str(e)}")
    
    async def close(self) -> None:
        """Close HTTP client connections."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
