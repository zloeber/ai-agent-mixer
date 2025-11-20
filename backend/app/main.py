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
from app.schemas.config import RootConfig, LogLevel
from app.services.config_manager import (
    load_config,
    save_config,
    validate_config_yaml,
)

# Global state
app_state: Dict[str, Any] = {
    "config": None,
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
