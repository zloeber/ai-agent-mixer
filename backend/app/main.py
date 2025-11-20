"""Main FastAPI application."""

import logging
from contextlib import asynccontextmanager
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.core.logging import setup_logging, get_logger
from app.core.websocket_manager import connection_manager
from app.core.orchestrator import ConversationOrchestrator
from app.schemas.config import RootConfig, LogLevel, ModelConfig
from app.services.config_manager import (
    load_config,
    save_config,
    validate_config_yaml,
)
from app.services.ollama_client import OllamaClient, OllamaConnectionError, OllamaModelNotFoundError

# Global state
app_state: Dict[str, Any] = {
    "config": None,
    "orchestrator": None,
    "conversation_running": False,
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager.
    
    Handles startup and shutdown events.
    """
    # Startup
    logger = get_logger(__name__)
    logger.info("Starting AI Agent Mixer backend...")
    
    # Initialize default logging
    setup_logging(LogLevel.INFO)
    
    yield
    
    # Shutdown
    logger.info("Shutting down AI Agent Mixer backend...")


# Create FastAPI app
app = FastAPI(
    title="AI Agent Mixer API",
    description="Backend API for Synthetic AI Conversation Orchestrator",
    version="0.1.0",
    lifespan=lifespan,
)

# Configure CORS
origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handlers
@app.exception_handler(ValidationError)
async def validation_exception_handler(request, exc: ValidationError):
    """Handle Pydantic validation errors."""
    errors = []
    for error in exc.errors():
        loc = " -> ".join(str(l) for l in error['loc'])
        errors.append({"location": loc, "message": error['msg']})
    
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Configuration validation failed",
            "errors": errors
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    """Handle general exceptions."""
    logger = get_logger(__name__)
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "config_loaded": app_state["config"] is not None,
    }


# Configuration endpoints
@app.post("/api/config/import")
async def import_config(config_dict: Dict[str, Any]):
    """Import configuration from JSON/dict.
    
    Args:
        config_dict: Configuration as dictionary
        
    Returns:
        Success message with config summary
    """
    try:
        config = RootConfig(**config_dict)
        config.validate_starting_agent()
        
        # Store in app state
        app_state["config"] = config
        
        # Update logging configuration
        setup_logging(
            config.logging.level,
            config.logging.output_directory
        )
        
        logger = get_logger(__name__)
        logger.info("Configuration imported successfully")
        
        return {
            "status": "success",
            "message": "Configuration imported successfully",
            "agents": list(config.agents.keys()),
            "starting_agent": config.conversation.starting_agent,
        }
        
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/config/export")
async def export_config():
    """Export current configuration.
    
    Returns:
        Current configuration as JSON
    """
    if app_state["config"] is None:
        raise HTTPException(status_code=404, detail="No configuration loaded")
    
    return app_state["config"].model_dump(mode='json', exclude_none=True)


@app.post("/api/config/validate")
async def validate_config(yaml_content: str):
    """Validate YAML configuration content.
    
    Args:
        yaml_content: YAML configuration as string
        
    Returns:
        Validation result with errors if any
    """
    is_valid, errors = validate_config_yaml(yaml_content)
    
    return {
        "valid": is_valid,
        "errors": errors,
    }


@app.post("/api/config/upload")
async def upload_config_file(file: UploadFile = File(...)):
    """Upload and import configuration from YAML file.
    
    Args:
        file: Uploaded YAML file
        
    Returns:
        Import result
    """
    try:
        # Read file content
        content = await file.read()
        yaml_content = content.decode('utf-8')
        
        # Validate first
        is_valid, errors = validate_config_yaml(yaml_content)
        if not is_valid:
            raise HTTPException(
                status_code=422,
                detail={"message": "Configuration validation failed", "errors": errors}
            )
        
        # Import if valid
        import yaml
        from app.services.config_manager import _substitute_env_vars
        
        content = _substitute_env_vars(yaml_content)
        config_dict = yaml.safe_load(content)
        
        config = RootConfig(**config_dict)
        config.validate_starting_agent()
        
        # Store in app state
        app_state["config"] = config
        
        # Update logging configuration
        setup_logging(
            config.logging.level,
            config.logging.output_directory
        )
        
        logger = get_logger(__name__)
        logger.info(f"Configuration uploaded from file: {file.filename}")
        
        return {
            "status": "success",
            "message": f"Configuration from {file.filename} imported successfully",
            "agents": list(config.agents.keys()),
            "starting_agent": config.conversation.starting_agent,
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/config/schema")
async def get_config_schema():
    """Get JSON schema for configuration validation.
    
    Returns:
        JSON schema for RootConfig
    """
    return RootConfig.model_json_schema()


# WebSocket endpoint
@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket endpoint for real-time communication.
    
    Args:
        websocket: WebSocket connection
        client_id: Unique client identifier
    """
    await connection_manager.connect(client_id, websocket)
    logger = get_logger(__name__)
    
    try:
        # Send welcome message
        await connection_manager.send_personal_message(
            {
                "type": "connected",
                "message": "Connected to AI Agent Mixer",
                "client_id": client_id,
            },
            client_id
        )
        
        # Keep connection alive and handle messages
        while True:
            try:
                # Receive message from client
                data = await websocket.receive_json()
                
                # Handle different message types
                if data.get("type") == "pong":
                    # Heartbeat response
                    logger.debug(f"Received pong from {client_id}")
                elif data.get("type") == "ping":
                    # Send pong response
                    await connection_manager.send_personal_message(
                        {"type": "pong"},
                        client_id
                    )
                else:
                    # Echo or handle other message types
                    logger.info(f"Received message from {client_id}: {data}")
                    
            except WebSocketDisconnect:
                logger.info(f"Client {client_id} disconnected")
                break
            except Exception as e:
                logger.error(f"Error in WebSocket connection {client_id}: {e}")
                break
                
    finally:
        await connection_manager.disconnect(client_id)


# WebSocket status endpoint
@app.get("/api/ws/status")
async def websocket_status():
    """Get WebSocket connection status.
    
    Returns:
        Status of WebSocket connections
    """
    return {
        "active_connections": connection_manager.get_connection_count(),
    }


# Ollama testing endpoint
@app.post("/api/ollama/test-connection")
async def test_ollama_connection(model_config: ModelConfig):
    """Test connection to an Ollama instance.
    
    Args:
        model_config: Model configuration to test
        
    Returns:
        Connection test result
    """
    try:
        client = OllamaClient(model_config)
        await client.verify_connection()
        await client.close()
        
        return {
            "status": "success",
            "message": f"Successfully connected to {model_config.url} with model {model_config.model_name}",
            "url": model_config.url,
            "model": model_config.model_name
        }
        
    except OllamaConnectionError as e:
        return {
            "status": "error",
            "message": str(e),
            "url": model_config.url
        }
    except OllamaModelNotFoundError as e:
        return {
            "status": "error",
            "message": str(e),
            "url": model_config.url,
            "model": model_config.model_name
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Unexpected error: {str(e)}",
            "url": model_config.url
        }


# Conversation management endpoints
@app.post("/api/conversation/start")
async def start_conversation():
    """Start a new conversation.
    
    Returns:
        Conversation metadata
    """
    if app_state["config"] is None:
        raise HTTPException(status_code=400, detail="No configuration loaded")
    
    if app_state["conversation_running"]:
        raise HTTPException(status_code=400, detail="Conversation already running")
    
    try:
        logger = get_logger(__name__)
        
        # Create orchestrator
        orchestrator = ConversationOrchestrator(
            config=app_state["config"],
            websocket_manager=connection_manager
        )
        
        # Start conversation
        metadata = await orchestrator.start_conversation()
        
        # Store orchestrator
        app_state["orchestrator"] = orchestrator
        app_state["conversation_running"] = True
        
        logger.info(f"Conversation started: {metadata['conversation_id']}")
        
        # Run conversation in background
        import asyncio
        asyncio.create_task(_run_conversation_background())
        
        return {
            "status": "started",
            **metadata
        }
        
    except Exception as e:
        logger = get_logger(__name__)
        logger.error(f"Error starting conversation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def _run_conversation_background():
    """Run conversation in the background."""
    logger = get_logger(__name__)
    try:
        orchestrator = app_state["orchestrator"]
        if orchestrator:
            final_state = await orchestrator.run_conversation()
            logger.info("Conversation completed successfully")
    except Exception as e:
        logger.error(f"Error in conversation: {e}", exc_info=True)
    finally:
        app_state["conversation_running"] = False


@app.post("/api/conversation/stop")
async def stop_conversation():
    """Stop the current conversation.
    
    Returns:
        Stop result
    """
    if not app_state["conversation_running"]:
        raise HTTPException(status_code=400, detail="No conversation running")
    
    # TODO: Implement graceful stop
    app_state["conversation_running"] = False
    app_state["orchestrator"] = None
    
    return {
        "status": "stopped",
        "message": "Conversation stopped"
    }


@app.get("/api/conversation/status")
async def get_conversation_status():
    """Get current conversation status.
    
    Returns:
        Conversation status
    """
    orchestrator = app_state["orchestrator"]
    
    if orchestrator and app_state["conversation_running"]:
        state = orchestrator.get_current_state()
        if state:
            return {
                "running": True,
                "current_cycle": state["current_cycle"],
                "message_count": len(state["messages"]),
                "should_terminate": state.get("should_terminate", False),
                "termination_reason": state.get("termination_reason")
            }
    
    return {
        "running": False,
        "message": "No conversation running"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
