"""
JSON Utilities Module

This module provides utilities for handling JSON serialization of complex data types,
including binary data and non-UTF-8 characters.
"""

import base64
import json
from datetime import datetime, date
from decimal import Decimal
import logging

# Get logger for this module
logger = logging.getLogger('db_data_extractor.utils.json_utils')

class OracleJSONEncoder(json.JSONEncoder):
    """
    Custom JSON encoder for Oracle data types and binary data.
    Handles special data types that are not natively JSON serializable.
    """
    def default(self, obj):
        try:
            # Handle binary data
            if isinstance(obj, bytes):
                return {
                    "_type": "binary",
                    "encoding": "base64",
                    "data": base64.b64encode(obj).decode('ascii')
                }
            
            # Handle dates and times
            if isinstance(obj, (datetime, date)):
                return obj.isoformat()
            
            # Handle Decimal
            if isinstance(obj, Decimal):
                return float(obj)
                
            # Handle other types by converting to string
            if not isinstance(obj, (str, int, float, bool, list, dict, type(None))):
                return str(obj)
                
            return super().default(obj)
        except Exception as e:
            logger.warning(f"JSON encoding error for {type(obj)}: {str(e)}")
            return "[UNCONVERTIBLE DATA]"

def safe_json_dumps(data):
    """
    Safely convert data to JSON string, handling binary data and non-UTF-8 characters.
    
    Args:
        data: The data to convert to JSON
        
    Returns:
        str: JSON string representation of the data
    """
    try:
        return json.dumps(data, cls=OracleJSONEncoder)
    except Exception as e:
        logger.error(f"JSON serialization error: {str(e)}")
        # Try a more aggressive approach for problematic data
        return json.dumps(sanitize_for_json(data))

def sanitize_for_json(data):
    """
    Recursively sanitize data to ensure it can be serialized to JSON.
    
    Args:
        data: The data to sanitize
        
    Returns:
        The sanitized data
    """
    if isinstance(data, dict):
        return {k: sanitize_for_json(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_for_json(item) for item in data]
    elif isinstance(data, bytes):
        try:
            return f"[BINARY: {base64.b64encode(data).decode('ascii')}]"
        except Exception as e:
            logger.warning(f"Failed to encode binary data: {str(e)}")
            return "[BINARY DATA]"
    elif isinstance(data, (datetime, date)):
        return data.isoformat()
    elif isinstance(data, Decimal):
        return float(data)
    elif data is None or isinstance(data, (str, int, float, bool)):
        return data
    else:
        try:
            return str(data)
        except Exception as e:
            logger.warning(f"Failed to convert {type(data)} to string: {str(e)}")
            return "[UNCONVERTIBLE DATA]"
