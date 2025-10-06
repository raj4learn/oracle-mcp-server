# Relative Path: db_data_extractor\utils\log_utils.py
"""
Logging Utilities Module

This module provides tools for consistent logging patterns across the application,
including function entry/exit logging with parameter and response tracking.
"""

import logging
import functools
import inspect
import json
from typing import Any, Callable, Dict, Tuple, Optional

def is_printable(obj: Any) -> bool:
    """
    Determine if an object can be safely printed/logged.
    
    Args:
        obj: Any Python object
        
    Returns:
        bool: True if the object can be safely printed
    """
    try:
        # Try to convert to string or JSON
        if isinstance(obj, (str, int, float, bool, type(None))):
            return True
        elif isinstance(obj, (list, tuple, dict)):
            json.dumps(obj)
            return True
        elif hasattr(obj, '__dict__'):
            # For custom objects, check if they have a readable __dict__
            json.dumps(obj.__dict__)
            return True
        return False
    except (TypeError, OverflowError, ValueError):
        return False

def get_function_params(func: Callable, args: Tuple, kwargs: Dict) -> Dict:
    """
    Get function parameters with their values.
    
    Args:
        func: The function
        args: Positional arguments
        kwargs: Keyword arguments
        
    Returns:
        Dict: Parameter names mapped to their values
    """
    try:
        signature = inspect.signature(func)
        bound_args = signature.bind(*args, **kwargs)
        bound_args.apply_defaults()
        
        # Filter out self/cls for methods
        params = {k: v for k, v in bound_args.arguments.items() 
                    if k not in ('self', 'cls')}
        return params
    except Exception:
        # If parameter binding fails, just return a simple dict of args and kwargs
        params = {}
        for i, arg in enumerate(args):
            if i == 0 and str(type(arg).__name__).endswith(('Explorer', 'Connection')):
                continue  # Skip self/cls
            params[f'arg{i}'] = arg
        params.update(kwargs)
        return params

def log_entry_exit(logger_name: Optional[str] = None):
    """
    Decorator to log function entry and exit with parameters and return values.
    
    Args:
        logger_name: Optional logger name. If None, a logger will be created based on the module name.
        
    Returns:
        Function decorator
    """
    def decorator(func):
        # Get the logger
        logger = None
        if logger_name is None:
            logger = logging.getLogger(func.__module__)
        else:
            logger = logging.getLogger(logger_name)
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Get function parameters
            params = get_function_params(func, args, kwargs)
            
            # Log function entry
            function_name = f"{func.__qualname__}"
            params_count = len(params)
            
            if params_count > 0 and all(is_printable(v) for v in params.values()):
                logger.info(f"ENTER: {function_name} with params: {params}")
            else:
                logger.info(f"ENTER: {function_name} with {params_count} params")
            
            # Execute the function
            try:
                result = await func(*args, **kwargs)
                
                # Log function exit with result
                if result is not None and is_printable(result):
                    logger.info(f"EXIT: {function_name} returned: {result}")
                else:
                    if isinstance(result, dict) and 'count' in result:
                        count = result.get('count', 0)
                        logger.info(f"EXIT: {function_name} returned {count} items")
                    else:
                        logger.info(f"EXIT: {function_name} completed successfully")
                
                return result
            except Exception as e:
                logger.error(f"ERROR: {function_name} failed with: {str(e)}")
                raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Get function parameters
            params = get_function_params(func, args, kwargs)
            
            # Log function entry
            function_name = f"{func.__qualname__}"
            params_count = len(params)
            
            if params_count > 0 and all(is_printable(v) for v in params.values()):
                logger.info(f"ENTER: {function_name} with params: {params}")
            else:
                logger.info(f"ENTER: {function_name} with {params_count} params")
            
            # Execute the function
            try:
                result = func(*args, **kwargs)
                
                # Log function exit with result
                if result is not None and is_printable(result):
                    logger.info(f"EXIT: {function_name} returned: {result}")
                else:
                    if isinstance(result, dict) and 'count' in result:
                        count = result.get('count', 0)
                        logger.info(f"EXIT: {function_name} returned {count} items")
                    else:
                        logger.info(f"EXIT: {function_name} completed successfully")
                
                return result
            except Exception as e:
                logger.error(f"ERROR: {function_name} failed with: {str(e)}")
                raise
        
        # Return the appropriate wrapper based on whether the function is async or not
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator
