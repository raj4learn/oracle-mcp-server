# Relative Path: db_data_extractor\utils\validation.py
# SQL validation and error handling utilities
"""
This module provides utilities for SQL validation and error handling.
It includes functions to validate SQL queries, check for SQL injection attempts,
and standardize error handling across the application.
"""

import logging
import re
import traceback
from typing import Optional, Tuple, Any, Callable, TypeVar
from functools import wraps

logger = logging.getLogger('db_data_extractor.utils.validation')

T = TypeVar('T')

# List of potentially dangerous SQL keywords and patterns
DANGEROUS_SQL_PATTERNS = [
    r';\s*DROP\s+', 
    r';\s*DELETE\s+',
    r';\s*TRUNCATE\s+',
    r';\s*ALTER\s+',
    r';\s*CREATE\s+',
    r';\s*INSERT\s+',
    r';\s*UPDATE\s+',
    r'EXEC\s+',
    r'EXECUTE\s+',
    r'xp_cmdshell',
    r'sp_',
    r'--',
    r'/\*.*\*/'
]

class SQLValidationError(Exception):
    """Exception raised for SQL validation errors."""
    pass

class DatabaseOperationError(Exception):
    """Exception raised for database operation errors."""
    pass

def validate_sql_query(query: str) -> Tuple[bool, Optional[str]]:
    """
    Validates a SQL query for potential SQL injection or dangerous operations.
    
    Args:
        query (str): The SQL query to validate
        
    Returns:
        Tuple[bool, Optional[str]]: A tuple containing:
            - Boolean indicating if the query is valid (True) or potentially dangerous (False)
            - Error message if validation fails, None otherwise
    """
    # Check for dangerous patterns
    upper_query = query.upper()
    
    # Check for multiple statements (basic check)
    if ';' in query and not (';' in query and "'" in query and query.find(';') > query.find("'")):
        return False, "Multiple SQL statements are not allowed"
    
    # Check for dangerous patterns
    for pattern in DANGEROUS_SQL_PATTERNS:
        if re.search(pattern, upper_query, re.IGNORECASE):
            return False, f"Potentially dangerous SQL pattern detected: {pattern}"
    
    return True, None

def validate_where_clause(where_clause: Optional[str]) -> Tuple[bool, Optional[str]]:
    """
    Validates a WHERE clause for potential SQL injection or dangerous operations.
    
    Args:
        where_clause (Optional[str]): The WHERE clause to validate, or None
        
    Returns:
        Tuple[bool, Optional[str]]: A tuple containing:
            - Boolean indicating if the clause is valid (True) or potentially dangerous (False)
            - Error message if validation fails, None otherwise
    """
    if where_clause is None:
        return True, None
    
    # Check for dangerous patterns
    for pattern in DANGEROUS_SQL_PATTERNS:
        if re.search(pattern, where_clause, re.IGNORECASE):
            return False, f"Potentially dangerous SQL pattern detected in WHERE clause: {pattern}"
    
    # Additional checks specific to WHERE clauses
    if ';' in where_clause:
        return False, "Semicolons are not allowed in WHERE clauses"
    
    return True, None

def standardized_error_handler(func: Callable[..., T]) -> Callable[..., Any]:
    """
    Decorator for standardizing error handling across database operations.
    
    Args:
        func: The function to wrap with standardized error handling
        
    Returns:
        The wrapped function with standardized error handling
    """
    @wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        try:
            return func(*args, **kwargs)
        except SQLValidationError as e:
            logger.error(f"SQL Validation Error in {func.__name__}: {str(e)}")
            logger.debug(f"SQL Validation Error details: {traceback.format_exc()}")
            # Return a standardized error response
            return {
                "error": "validation_error",
                "message": str(e),
                "status": "error"
            }
        except DatabaseOperationError as e:
            logger.error(f"Database Operation Error in {func.__name__}: {str(e)}")
            logger.debug(f"Database Error details: {traceback.format_exc()}")
            # Return a standardized error response
            return {
                "error": "database_error",
                "message": str(e),
                "status": "error"
            }
        except Exception as e:
            logger.error(f"Unexpected Error in {func.__name__}: {str(e)}")
            logger.debug(f"Error details: {traceback.format_exc()}")
            # Return a standardized error response
            return {
                "error": "unexpected_error",
                "message": "An unexpected error occurred. Please check the logs for details.",
                "status": "error"
            }
    return wrapper
