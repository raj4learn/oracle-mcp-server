# Relative Path: oracle_mcp\tools\handlers.py
# Handler functions for Oracle MCP server
import logging

# Configure logging
logger = logging.getLogger('oracle_mcp')

def register_handlers(mcp_app, operation_map):
    """Register all handler functions with the MCP application."""
    
    # Add a dynamic greeting resource
    @mcp_app.resource("greeting://{name}")
    def get_greeting(name: str) -> str:
        """Get a personalized greeting"""
        return f"Hello, {name}!"

    # Define the oracle_mcp agent that connects external agents to the Oracle DB agent
    @mcp_app.prompt(
        name="oracle_mcp",
        description="""
        You are an Oracle MCP (Model Context Protocol) service that provides 
        a standardized interface for external agents to interact with Oracle databases.
        
        You receive requests from external agents, format them appropriately for the Oracle DB agent,
        then return the structured database information in a format the external agents can consume.
        
        Examples of what you can provide:
        1. Database schema information (packages, procedures, functions)
        2. Table structures and metadata
        3. Sample data from tables
        4. SQL query execution results
        
        You act as the gateway between external services and the Oracle database infrastructure.
        """
    )   
    
    def oracle_mcp_handler(prompt):
        """Handle requests to the Oracle MCP service"""
        pass