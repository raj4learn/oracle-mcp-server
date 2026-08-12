# Relative Path: db_data_extractor\standard\connection.py
"""
Oracle Connection Module

This module provides tools for connecting to Oracle databases, including
connection management, pooling, error handling, and connection configuration.
"""

import os
import time
import oracledb
import logging
from dotenv import load_dotenv
from typing import Dict, Any, Optional
from oracle_mcp.tools.db_models_std import ConnectionStatusResponse, ConnectionErrorResponse

# Get logger for this module
logger = logging.getLogger('db_data_extractor.standard.connection')
logger.info('Oracle Connection module loaded')

class OracleConnection:
    """
    Provides Oracle database connection management and utility functions.
    Can be used as a context manager with 'with' statements to automatically handle connections.
    
    When keep_alive is True, connections remain open after exiting the context manager,
    allowing for reuse across multiple operations for better performance.
    """
    def __init__(self, username=None, password=None, dsn=None, encoding=None, thick_mode=None, keep_alive=True):
        logger.debug("IN __init__")
        """
        Initialize connection parameters from arguments or environment variables.
        
        Args:
            username (str, optional): Oracle username
            password (str, optional): Oracle password
            dsn (str, optional): Oracle connection string
            encoding (str, optional): Character encoding for the connection
            thick_mode (bool, optional): Use thick mode Oracle client if True
            keep_alive (bool, optional): When True, connections remain open after context manager exit
        """
        logger.info('__init__: Initializing OracleConnection')
        # Load environment variables if not explicitly provided
        load_dotenv(override=True)
        
        self.username = username or os.getenv("ORACLE_USERNAME")
        self.password = password or os.getenv("ORACLE_PASSWORD")
        self.dsn = dsn or os.getenv("ORACLE_DSN")
        self.encoding = encoding or os.getenv("ORACLE_ENCODING", "UTF-8")
        
        # Convert thick_mode to boolean from string if from env var
        thick_mode_env = os.getenv("ORACLE_THICK_MODE", "False")
        self.thick_mode = thick_mode if thick_mode is not None else thick_mode_env.lower() in ("true", "1", "yes")
        
        # Initialize connection object to None
        self.conn = None
        # Control whether to keep connection alive after context manager exit
        self.keep_alive = keep_alive
        logger.info(f'OracleConnection initialized with DSN: {self.dsn}, user: {self.username}, thick_mode: {self.thick_mode}, keep_alive: {self.keep_alive}')
        logger.debug("OUT __init__")

    def get_fresh_connection(self) -> oracledb.Connection:
        """
        Create a completely new connection to the Oracle database, ignoring any existing connection.
        This is useful when you want to ensure a fresh connection for a new operation.
        
        Returns:
            oracledb.Connection: A fresh database connection object
        
        Raises:
            oracledb.Error: If connection fails
        """
        logger.info('get_fresh_connection: Creating a completely fresh Oracle connection')
        
        # Close any existing connection first
        if self.conn is not None:
            try:
                self.conn.close()
                logger.debug('get_fresh_connection: Closed existing connection')
            except Exception as e:
                logger.warning(f'get_fresh_connection: Error closing existing connection: {str(e)}')
            finally:
                self.conn = None
        
        # Now create a completely fresh connection
        return self.connect()
    
    def connect(self) -> oracledb.Connection:
        logger.debug("IN connect")
        """
        Establish a connection to the Oracle database.
        
        Returns:
            oracledb.Connection: The database connection object
        
        Raises:
            oracledb.Error: If connection fails
        """
        logger.info('__connect__: Connecting to Oracle database')
        
        # Check if we have required connection parameters
        if not self.username or not self.password or not self.dsn:
            logger.error("Missing required connection parameters (username, password, or DSN)")
            raise ValueError("Missing required connection parameters. Check environment variables or provide them explicitly.")
        
        if self.conn is not None:
            try:
                # Test if connection is still valid
                logger.debug('__connect__: Testing existing connection')
                cursor = self.conn.cursor()
                cursor.execute("SELECT 1 FROM DUAL")
                cursor.close()
                logger.debug('__connect__: Existing connection is valid. since returning...')
                logger.debug("OUT connect")
                return self.conn
            except Exception as e:
                logger.warning(f'__connect__: Existing connection is invalid: {str(e)}. Creating new connection...')
                # Close the invalid connection properly before creating a new one
                try:
                    if self.conn:
                        self.conn.close()
                except Exception:
                    pass
                self.conn = None

        # Maximum number of connection attempts
        max_attempts = 2
        attempt = 0
        last_error = None
        
        while attempt < max_attempts:
            attempt += 1
            try:
                logger.debug(f'__connect__: Connection attempt {attempt}/{max_attempts}')
                # Configure thick mode if requested
                if self.thick_mode:
                    logger.debug('__connect__: Using thick mode Oracle client')
                    oracledb.init_oracle_client()
                
                # Connect to the database
                logger.debug('__connect__: Getting Connection from Oracle database')
                logger.debug(f"__connect__: Connecting to Oracle with username: {self.username}, dsn: {self.dsn}")
                
                # Create the connection
                self.conn = oracledb.connect(
                    user=self.username,
                    password=self.password,
                    dsn=self.dsn
                )
                
                # Test the connection with a simple query
                cursor = self.conn.cursor()
                cursor.execute("SELECT 1 FROM DUAL")
                cursor.close()
                
                logger.info(f'__connect__: Successfully connected to Oracle database on attempt {attempt}')
                return self.conn
            except Exception as e:
                last_error = e
                logger.warning(f"Connection attempt {attempt} failed: {str(e)}")
                # Wait before retrying (exponential backoff)
                if attempt < max_attempts:
                    wait_time = 2 ** attempt  # 2, 4, 8 seconds
                    logger.info(f"Waiting {wait_time} seconds before retry...")
                    time.sleep(wait_time)
        
        # If we get here, all connection attempts failed
        logger.error(f"Failed to connect to Oracle database after {max_attempts} attempts. Last error: {str(last_error)}")
        raise last_error or Exception("Failed to connect to Oracle database")
        
        logger.debug("OUT connect")

    def close(self) -> None:
        logger.debug("IN close")
        """
        Close the database connection if it exists.
        """
        if self.conn is not None:
            try:
                self.conn.close()
                logger.debug('__close__: Database connection closed successfully')
            except Exception as e:
                logger.warning(f"Error closing connection: {str(e)}")
                logger.debug(f"Warning: Error closing connection: {str(e)}")
            finally:
                self.conn = None
        logger.debug("OUT close")

    def force_close(self) -> None:
        logger.debug("IN force_close")
        """
        Explicitly force the connection to close regardless of keep_alive setting.
        Use this when you're completely done with the connection.
        """
        logger.debug('force_close: Forcing database connection to close')
        self.close()
        logger.debug("OUT force_close")

    def get_connection_info(self) -> Dict[str, Any]:
        logger.debug("IN get_connection_info")
        """
        Get information about the current connection.
        
        Returns:
            dict: Dictionary with connection information
        """
        logger.debug('__get_connection_info__: Retrieving connection information')
        if self.conn is None:
            logger.debug('__get_connection_info__: No active connection')
            logger.debug("OUT get_connection_info")
            return {"status": "disconnected"}
        
        # Check if connection is valid by trying a simple query
        try:
            logger.debug('Testing connection validity')
            cursor = self.conn.cursor()
            cursor.execute("SELECT 1 FROM DUAL")
            cursor.close()
            logger.debug('Connection is valid')
        except Exception as e:
            logger.warning(f'Connection validity check failed: {str(e)}')
            logger.debug("OUT get_connection_info")
            return {"status": "disconnected"}
        
        connection_info = {
            "status": "connected",
            "username": self.username,
            "dsn": self.dsn,
            "version": self.conn.version,
            "encoding": self.encoding,
            "thick_mode": self.thick_mode
        }
        logger.debug(f'Connection info: {connection_info}')
        logger.debug("OUT get_connection_info")
        return connection_info

    def __enter__(self):
        logger.debug("IN __enter__")
        """
        Enter method for context manager support, allowing use in 'with' statements.
        
        Returns:
            oracledb.Connection: The actual database connection object
        """
        logger.debug('__enter__: Entering OracleConnection context')
        result = self.connect()
        logger.debug("OUT __enter__")
        return result

    def get_connection_status(self) -> ConnectionStatusResponse:
        logger.debug("IN get_connection_status")
        """
        Returns a structured response indicating connection status and metadata.
        """
        try:
            self.connect()
            logger.debug("OUT get_connection_status")
            return ConnectionStatusResponse(
                is_connected=True,
                dsn=getattr(self, 'dsn', None),
                username=getattr(self, 'username', None),
                thick_mode=getattr(self, 'thick_mode', None),
                message="Connection successful"
            )
        except Exception as e:
            logger.error(f"Connection failed: {str(e)}")
            logger.debug("OUT get_connection_status")
            return ConnectionErrorResponse(
                is_connected=False,
                error=str(e),
                dsn=getattr(self, 'dsn', None),
                username=getattr(self, 'username', None),
                thick_mode=getattr(self, 'thick_mode', None)
            )


    def __exit__(self, exc_type, exc_value, traceback):
        logger.debug("IN __exit__")
        if not self.keep_alive:
            self.close()
        logger.debug("OUT __exit__")

