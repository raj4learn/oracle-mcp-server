# Relative Path: main.py
# Main entry point for Oracle MCP Server
 

# Import dotenv for environment variable management
from dotenv import load_dotenv

# Import our modular components
from oracle_mcp.tools.server import create_server, start_server
from oracle_mcp.tools.db_operations import register_tools
from oracle_mcp.tools.handlers import register_handlers
from oracle_mcp.utils.logger import setup_logging, get_logger

# Load environment variables from .env file
load_dotenv(override=True)

# Configure common logging once for the app (file handler by default)
setup_logging(enable_console=False)
logger = get_logger()

def start_oracle_mcp():
    """Initialize and start the Oracle MCP server."""
    # Create the server instance
    oracleMCP = create_server()
    
    # Register database operation tools
    register_tools(oracleMCP)       # Tools are registered via decorator within this call
    
    # Pass oracleMCP. The operation_map is not used by register_handlers.
    # We can pass None, or modify register_handlers to not expect operation_map.
    # For now, passing None is the simplest change to main.py.
    register_handlers(oracleMCP, None)
    
    logger.info("Oracle MCP tools and handlers initialized")
    
    # Start the server
    start_server(oracleMCP)

if __name__ == "__main__":
    start_oracle_mcp()

# End of file