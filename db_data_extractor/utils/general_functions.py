
# Relative Path: db_data_extractor\utils\general_functions.py
"""
General Functions Module

This module provides specialized tools for accessing and analyzing forms stored in Oracle database,
including forms from packages, procedures, functions, triggers, and other database objects.
These forms help with issue and bug analysis.
"""

import logging
from datetime import datetime
from typing import Optional
# from db_data_extractor.standard.connection import OracleConnection

# Configure logger for this module
logger = logging.getLogger('db_data_extractor.utils.general_functions')
logger.info('General functions module loaded')

class GeneralFunctions:
    def __init__(self, connection=None):
        """
        Initialize with an existing connection or create a new one.
        
        Args:
            connection (OracleConnection, optional): Existing connection to use
        """
        # self.connection = connection or OracleConnection()
        logger.info("GeneralFunctions initialized with connection")
    
    def safe_decode(self, index: int, value: any) -> any:
        """
        Safely decode values from the database to appropriate Python types.
        
        Args:
            index (int): Column index in the result row
            value (any): Value to decode/convert
            
        Returns:
            any: Decoded/converted value suitable for JSON serialization
        """
        try:
            logger.debug(f"Decoding value at index {index}: {type(value)}")
            
            if value is None:
                return None
                
            if isinstance(value, bytes):
                try:
                    return value.decode("utf-8")
                except UnicodeDecodeError:
                    # Fall back to hex representation if not valid UTF-8
                    return value.hex()
                    
            elif isinstance(value, datetime):
                return value.isoformat()
                
            elif isinstance(value, (int, float, bool, str)):
                # These types are already JSON serializable
                return value
                
            # Handle other types that might need special conversion
            return str(value)
            
        except Exception as e:
            logger.warning(f"Error decoding value at index {index}: {str(e)}")
            # Return a safe default rather than failing the entire operation
            return f"[Error decoding: {str(e)}]"

