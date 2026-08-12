# Relative Path: oracle_mcp\config.py
# Centralized configuration for Oracle MCP Server
"""
This module provides centralized configuration settings for the Oracle MCP Server.
All configuration values should be defined here and imported by other modules.
Environment variables can override these default values.
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

# Server configuration
SERVER_HOST = os.getenv('MCP_HOST', '127.0.0.1')
SERVER_PORT = int(os.getenv('MCP_PORT', 8000))
SERVER_TRANSPORT = os.getenv('MCP_TRANSPORT', 'stdio')

# Database configuration
DEFAULT_SCHEMA = os.getenv('MCP_DEFAULT_SCHEMA', 'SCOTT')
DEFAULT_QUERY_LIMIT = int(os.getenv('MCP_DEFAULT_QUERY_LIMIT', 200))
DEFAULT_LARGE_QUERY_LIMIT = int(os.getenv('MCP_LARGE_QUERY_LIMIT', 1000))
DEFAULT_SOURCE_CODE_LIMIT = int(os.getenv('MCP_SOURCE_CODE_LIMIT', 8000))

# Logging configuration
LOG_DIRECTORY = os.getenv('LOG_DIRECTORY', 'logs')
LOG_FILENAME = os.getenv('LOG_FILENAME', 'oracle_mcp.log')
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# Knowledge base configuration
KNOWLEDGE_BASE_DIR = ".windsurf"
