# Relative Path: oracle_mcp\tools\server.py
# Server configuration and startup for Oracle MCP
import logging
import sys
from fastmcp import FastMCP

# Import centralized configuration
from oracle_mcp.config import SERVER_HOST, SERVER_PORT, SERVER_TRANSPORT

# Configure logging
logger = logging.getLogger('oracle_mcp')

def create_server():
    """Create and configure the FastMCP server."""
    # Create the application
    oracleMCP = FastMCP("Oracle MCP Service")

    # Configure the FastMCP server using centralized configuration
    oracleMCP.host = SERVER_HOST
    oracleMCP.port = SERVER_PORT

    return oracleMCP

def start_server(mcp_app):
    """Start the FastMCP server."""
    try:
        # Add additional debug logging for troubleshooting
        logger.info(f"Starting Oracle MCP server with host={SERVER_HOST}, port={SERVER_PORT}, transport={SERVER_TRANSPORT}")
        
        # Run with configured settings from centralized configuration
        mcp_app.run(transport=SERVER_TRANSPORT)
    except KeyboardInterrupt:
        print("\nOracle MCP Service stopped.", file=sys.stderr)
    except Exception as e:
        print(f"Error starting Oracle MCP Service: {str(e)}", file=sys.stderr)
        print("Check your environment configuration and dependencies.", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)