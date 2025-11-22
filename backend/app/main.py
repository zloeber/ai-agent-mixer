"""Main FastAPI application."""

import logging
from contextlib import asynccontextmanager
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException, UploadFile, File, WebSocket, WebSocketDisconnect, Request, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import ValidationError

from app.core.logging import setup_logging, get_logger
from app.core.websocket_manager import connection_manager
from app.core.orchestrator import ConversationOrchestrator
from app.core.exceptions import (
    AIAgentMixerException,
    ConfigurationError,
    InvalidConfigError,
    OllamaConnectionError,
    OllamaModelNotFoundError,
    MCPServerError,
    AgentExecutionError,
)
from app.schemas.config import RootConfig, LogLevel, ModelConfig
from app.services.config_manager import (
    load_config,
    save_config,
    validate_config_yaml,
)
from app.services.ollama_client import OllamaClient, OllamaConnectionError, OllamaModelNotFoundError
from app.services.mcp_manager import get_mcp_manager

# Global state
app_state: Dict[str, Any] = {
    "config": None,
    "orchestrator": None,
    "conversation_running": False,
    "conversation_paused": False,
    "metrics": {
        "requests_total": 0,
        "requests_errors": 0,
        "conversations_started": 0,
        "conversations_completed": 0,
        "websocket_connections_total": 0,
    }
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
    
    # Initialize MCP manager
    mcp_manager = get_mcp_manager()
    logger.info("MCP Manager initialized")
    
    # Start global MCP servers if config is loaded
    if app_state.get("config"):
        config = app_state["config"]
        global_servers = config.mcp_servers.global_servers
        if global_servers:
            logger.info(f"Starting {len(global_servers)} global MCP servers")
            for server_config in global_servers:
                try:
                    await mcp_manager.start_server(server_config)
                    logger.info(f"Started global MCP server: {server_config.name}")
                except Exception as e:
                    logger.error(f"Failed to start global MCP server {server_config.name}: {e}")
            
            # Start health monitoring
            await mcp_manager.start_health_monitoring()
    
    yield
    
    # Shutdown
    logger.info("Shutting down AI Agent Mixer backend...")
    
    # Stop all MCP servers
    await mcp_manager.stop_all_servers()
    logger.info("All MCP servers stopped")


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


# Middleware to track metrics
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Middleware to track request metrics."""
    app_state["metrics"]["requests_total"] += 1
    
    try:
        response = await call_next(request)
        if response.status_code >= 400:
            app_state["metrics"]["requests_errors"] += 1
        return response
    except Exception as e:
        app_state["metrics"]["requests_errors"] += 1
        raise


# Global exception handlers
@app.exception_handler(AIAgentMixerException)
async def custom_exception_handler(request: Request, exc: AIAgentMixerException):
    """Handle custom application exceptions."""
    logger = get_logger(__name__)
    logger.error(
        f"Application error: {exc.message}",
        extra={"details": exc.details, "status_code": exc.status_code}
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.__class__.__name__,
            "message": exc.message,
            "details": exc.details,
        }
    )


@app.exception_handler(ConfigurationError)
async def configuration_error_handler(request: Request, exc: ConfigurationError):
    """Handle configuration errors."""
    logger = get_logger(__name__)
    logger.error(f"Configuration error: {exc.message}", extra={"details": exc.details})
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "ConfigurationError",
            "message": exc.message,
            "details": exc.details,
        }
    )
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


# Metrics endpoint for monitoring
@app.get("/metrics")
async def metrics():
    """
    Prometheus-compatible metrics endpoint.
    
    Returns:
        Application metrics in Prometheus text format
    """
    metrics_data = app_state["metrics"]
    mcp_manager = get_mcp_manager()
    mcp_statuses = await mcp_manager.get_all_statuses()
    
    # Calculate derived metrics
    healthy_servers = sum(1 for s in mcp_statuses.values() if s.healthy)
    total_servers = len(mcp_statuses)
    
    # Format as Prometheus metrics
    metrics_text = f"""# HELP requests_total Total number of HTTP requests
# TYPE requests_total counter
requests_total {metrics_data['requests_total']}

# HELP requests_errors Total number of HTTP errors
# TYPE requests_errors counter
requests_errors {metrics_data['requests_errors']}

# HELP conversations_started Total number of conversations started
# TYPE conversations_started counter
conversations_started {metrics_data['conversations_started']}

# HELP conversations_completed Total number of conversations completed
# TYPE conversations_completed counter
conversations_completed {metrics_data['conversations_completed']}

# HELP websocket_connections_active Current active WebSocket connections
# TYPE websocket_connections_active gauge
websocket_connections_active {connection_manager.get_connection_count()}

# HELP websocket_connections_total Total WebSocket connections
# TYPE websocket_connections_total counter
websocket_connections_total {metrics_data['websocket_connections_total']}

# HELP mcp_servers_total Total number of MCP servers
# TYPE mcp_servers_total gauge
mcp_servers_total {total_servers}

# HELP mcp_servers_healthy Number of healthy MCP servers
# TYPE mcp_servers_healthy gauge
mcp_servers_healthy {healthy_servers}

# HELP conversation_running Whether a conversation is currently running
# TYPE conversation_running gauge
conversation_running {1 if app_state['conversation_running'] else 0}
"""
    
    return Response(
        content=metrics_text,
        media_type="text/plain; version=0.0.4"
    )


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
        
        # Start global MCP servers
        mcp_manager = get_mcp_manager()
        global_servers = config.mcp_servers.global_servers
        started_servers = []
        failed_servers = []
        
        if global_servers:
            logger.info(f"Starting {len(global_servers)} global MCP servers")
            for server_config in global_servers:
                try:
                    success = await mcp_manager.start_server(server_config)
                    if success:
                        started_servers.append(server_config.name)
                        logger.info(f"Started global MCP server: {server_config.name}")
                    else:
                        failed_servers.append(server_config.name)
                except Exception as e:
                    failed_servers.append(server_config.name)
                    logger.error(f"Failed to start global MCP server {server_config.name}: {e}")
            
            # Start health monitoring if not already running
            await mcp_manager.start_health_monitoring()
        
        # Get starting agent from either conversation or conversations[0]
        starting_agent = None
        if config.conversation:
            starting_agent = config.conversation.starting_agent
        elif config.conversations:
            starting_agent = config.conversations[0].starting_agent
        
        return {
            "status": "success",
            "message": "Configuration imported successfully",
            "agents": list(config.agents.keys()),
            "starting_agent": starting_agent,
            "mcp_servers": {
                "started": started_servers,
                "failed": failed_servers,
                "total": len(global_servers)
            }
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
async def validate_config(yaml_content: str = Body(..., media_type="text/plain")):
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
        
        # Get starting agent from either conversation or conversations[0]
        starting_agent = None
        if config.conversation:
            starting_agent = config.conversation.starting_agent
        elif config.conversations:
            starting_agent = config.conversations[0].starting_agent
        
        return {
            "status": "success",
            "message": f"Configuration from {file.filename} imported successfully",
            "agents": list(config.agents.keys()),
            "starting_agent": starting_agent,
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
    app_state["metrics"]["websocket_connections_total"] += 1
    
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
@app.get("/api/conversation/scenarios")
async def list_scenarios():
    """List available conversation scenarios.
    
    Returns:
        List of available scenarios
    """
    if app_state["config"] is None:
        raise HTTPException(status_code=400, detail="No configuration loaded")
    
    try:
        config = app_state["config"]
        scenarios = config.list_scenarios()
        
        # Build detailed scenario info
        scenario_list = []
        for scenario_name in scenarios:
            scenario_config = config.get_conversation_config(scenario_name)
            scenario_list.append({
                "name": scenario_name,
                "goal": scenario_config.goal,
                "brevity": scenario_config.brevity,
                "max_cycles": scenario_config.max_cycles,
                "starting_agent": scenario_config.starting_agent,
                "agents_involved": scenario_config.agents_involved
            })
        
        return {
            "scenarios": scenario_list,
            "default": scenarios[0] if scenarios else None
        }
        
    except Exception as e:
        logger = get_logger(__name__)
        logger.error(f"Error listing scenarios: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/conversation/start")
async def start_conversation(
    scenario: str | None = None,
    max_cycles: int | None = None,
    starting_agent: str | None = None
):
    """Start a new conversation.
    
    Args:
        scenario: Optional scenario name to use (None = first/default)
        max_cycles: Optional override for maximum cycles
        starting_agent: Optional override for starting agent
    
    Returns:
        Conversation metadata
    """
    if app_state["config"] is None:
        raise HTTPException(status_code=400, detail="No configuration loaded")
    
    if app_state["conversation_running"]:
        raise HTTPException(status_code=400, detail="Conversation already running")
    
    try:
        logger = get_logger(__name__)
        
        # Create orchestrator with scenario selection
        orchestrator = ConversationOrchestrator(
            config=app_state["config"],
            websocket_manager=connection_manager,
            scenario_name=scenario,
            max_cycles_override=max_cycles,
            starting_agent_override=starting_agent
        )
        
        # Start conversation
        metadata = await orchestrator.start_conversation()
        
        # Store orchestrator
        app_state["orchestrator"] = orchestrator
        app_state["conversation_running"] = True
        app_state["metrics"]["conversations_started"] += 1
        
        scenario_info = f" (scenario: {scenario})" if scenario else ""
        overrides = []
        if max_cycles:
            overrides.append(f"max_cycles={max_cycles}")
        if starting_agent:
            overrides.append(f"starting_agent={starting_agent}")
        override_info = f" with overrides: {', '.join(overrides)}" if overrides else ""
        logger.info(f"Conversation started: {metadata['conversation_id']}{scenario_info}{override_info}")
        
        # Note: Don't auto-run conversation, wait for continue command
        # This allows step-by-step execution
        
        return {
            "status": "started",
            "scenario": scenario,
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
            app_state["metrics"]["conversations_completed"] += 1
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
    
    # Notify clients
    await connection_manager.broadcast({
        "type": "conversation_ended",
        "reason": "stopped_by_user"
    })
    
    return {
        "status": "stopped",
        "message": "Conversation stopped"
    }


@app.post("/api/conversation/pause")
async def pause_conversation():
    """Pause the current conversation.
    
    Returns:
        Pause result
    """
    if not app_state["conversation_running"]:
        raise HTTPException(status_code=400, detail="No conversation running")
    
    app_state["conversation_paused"] = True
    
    # Notify clients
    await connection_manager.broadcast({
        "type": "conversation_status",
        "status": "paused"
    })
    
    return {
        "status": "paused",
        "message": "Conversation paused"
    }


@app.post("/api/conversation/resume")
async def resume_conversation():
    """Resume a paused conversation.
    
    Returns:
        Resume result
    """
    if not app_state["conversation_running"]:
        raise HTTPException(status_code=400, detail="No conversation running")
    
    if not app_state.get("conversation_paused"):
        raise HTTPException(status_code=400, detail="Conversation is not paused")
    
    app_state["conversation_paused"] = False
    
    # Notify clients
    await connection_manager.broadcast({
        "type": "conversation_status",
        "status": "resumed"
    })
    
    return {
        "status": "resumed",
        "message": "Conversation resumed"
    }


@app.post("/api/conversation/continue")
async def continue_conversation(cycles: int = 1):
    """Continue conversation for a specific number of cycles.
    
    Args:
        cycles: Number of cycles to run (default: 1)
    
    Returns:
        Continuation result with updated state
    """
    logger = get_logger(__name__)
    
    if app_state["config"] is None:
        raise HTTPException(status_code=400, detail="No configuration loaded")
    
    orchestrator = app_state.get("orchestrator")
    if orchestrator is None:
        raise HTTPException(status_code=400, detail="No conversation started. Start a conversation first.")
    
    if cycles < 1 or cycles > 100:
        raise HTTPException(status_code=400, detail="Cycles must be between 1 and 100")
    
    try:
        # Mark as running if not already
        app_state["conversation_running"] = True
        
        # Run specified number of cycles
        final_state = await orchestrator.run_cycles(num_cycles=cycles)
        
        # Check if conversation ended
        if final_state.get("should_terminate", False):
            app_state["conversation_running"] = False
            app_state["metrics"]["conversations_completed"] += 1
            logger.info(f"Conversation completed after continuing {cycles} cycles")
        
        return {
            "status": "continued",
            "cycles_run": cycles,
            "current_cycle": final_state["current_cycle"],
            "terminated": final_state.get("should_terminate", False),
            "termination_reason": final_state.get("termination_reason"),
            "message_count": len(final_state["messages"])
        }
        
    except Exception as e:
        logger.error(f"Error continuing conversation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


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


# MCP Server Management endpoints
@app.get("/api/mcp/status")
async def get_mcp_status():
    """Get status of all MCP servers.
    
    Returns:
        Dictionary of server names to their status
    """
    mcp_manager = get_mcp_manager()
    statuses = await mcp_manager.get_all_statuses()
    
    return {
        "servers": {
            name: {
                "running": status.running,
                "healthy": status.healthy,
                "started_at": status.started_at.isoformat() if status.started_at else None,
                "error_message": status.error_message,
                "tools_count": len(status.tools_available),
                "tools": status.tools_available
            }
            for name, status in statuses.items()
        },
        "total_servers": len(statuses),
        "healthy_servers": sum(1 for s in statuses.values() if s.healthy)
    }


@app.get("/api/mcp/servers/{server_name}/status")
async def get_server_status(server_name: str):
    """Get status of a specific MCP server.
    
    Args:
        server_name: Name of the server
        
    Returns:
        Server status details
    """
    mcp_manager = get_mcp_manager()
    status = await mcp_manager.get_server_status(server_name)
    
    if not status:
        raise HTTPException(status_code=404, detail=f"MCP server {server_name} not found")
    
    return {
        "name": status.name,
        "running": status.running,
        "healthy": status.healthy,
        "started_at": status.started_at.isoformat() if status.started_at else None,
        "error_message": status.error_message,
        "tools_count": len(status.tools_available),
        "tools": status.tools_available
    }


@app.post("/api/mcp/servers/{server_name}/restart")
async def restart_server(server_name: str):
    """Restart a specific MCP server.
    
    Args:
        server_name: Name of the server
        
    Returns:
        Restart result
    """
    logger = get_logger(__name__)
    mcp_manager = get_mcp_manager()
    
    try:
        success = await mcp_manager.restart_server(server_name)
        
        if success:
            logger.info(f"MCP server {server_name} restarted successfully")
            return {
                "status": "success",
                "message": f"Server {server_name} restarted successfully"
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to restart server {server_name}"
            )
            
    except Exception as e:
        logger.error(f"Error restarting MCP server {server_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/mcp/tools")
async def get_all_tools():
    """Get all available tools from all MCP servers.
    
    Returns:
        List of all available tools with their metadata
    """
    mcp_manager = get_mcp_manager()
    
    all_tools = []
    servers = mcp_manager.get_all_servers()
    
    for server_name, instance in servers.items():
        if instance.healthy and instance.session:
            try:
                tools_result = await instance.session.list_tools()
                for tool in tools_result.tools:
                    all_tools.append({
                        "name": tool.name,
                        "description": tool.description or "",
                        "server": server_name,
                        "input_schema": tool.inputSchema
                    })
            except Exception as e:
                logger = get_logger(__name__)
                logger.error(f"Error listing tools from server {server_name}: {e}")
    
    return {
        "tools": all_tools,
        "total_count": len(all_tools)
    }


@app.get("/api/mcp/agents/{agent_id}/tools")
async def get_agent_tools(agent_id: str):
    """Get all tools available to a specific agent.
    
    Args:
        agent_id: ID of the agent
        
    Returns:
        List of tools available to the agent
    """
    if not app_state.get("config"):
        raise HTTPException(status_code=404, detail="No configuration loaded")
    
    config = app_state["config"]
    
    if agent_id not in config.agents:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
    
    agent_config = config.agents[agent_id]
    mcp_manager = get_mcp_manager()
    
    # Get global server names
    global_server_names = [s.name for s in config.mcp_servers.global_servers]
    
    # Get agent-specific server names
    agent_server_names = agent_config.mcp_servers
    
    # Get tools
    tools = await mcp_manager.get_tools_for_agent(
        agent_id=agent_id,
        global_server_names=global_server_names,
        agent_server_names=agent_server_names
    )
    
    return {
        "agent_id": agent_id,
        "tools": tools,
        "total_count": len(tools),
        "global_servers": global_server_names,
        "agent_servers": agent_server_names
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
