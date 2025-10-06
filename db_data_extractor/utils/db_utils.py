# Relative Path: db_data_extractor\utils\db_utils.py
# Database utility functions for asynchronous database operations

import asyncio
import logging
from typing import Callable, Optional, TypeVar, Union
import concurrent.futures

logger = logging.getLogger('db_data_extractor.common.utils.db_utils')

T = TypeVar('T')

async def run_db_query(func: Callable[..., T], timeout: Optional[float] = None) -> Union[T, list]:
    """
    Execute a database query function asynchronously in a thread pool executor.
    
    This function allows potentially blocking database operations to run in a separate thread,
    preventing the main event loop from being blocked. It's particularly useful for
    long-running queries or when multiple queries need to be executed concurrently.
    
    Args:
        func (Callable): The database query function to execute. This should be a synchronous
                        function that performs the actual database operation.
        timeout (float, optional): Maximum time in seconds to wait for the query to complete.
                                If None, waits indefinitely. Default is None.
    
    Returns:
        The result of the database query function or an empty list if an error occurs.
    
    Example:
        ```python
        async def get_user_data(user_id):
            def _query():
                return db_connection.execute("SELECT * FROM users WHERE id = ?", [user_id])
            
            return await run_db_query(_query)
        ```
    """
    try:
        loop = asyncio.get_event_loop()
        if timeout is not None:
            # Use asyncio.wait_for to implement timeout
            return await asyncio.wait_for(
                loop.run_in_executor(None, func),
                timeout=timeout
            )
        else:
            return await loop.run_in_executor(None, func)
    except asyncio.TimeoutError:
        logger.error(f"Database query timed out after {timeout} seconds")
        return []
    except concurrent.futures.CancelledError:
        logger.error("Database query was cancelled")
        return []
    except Exception as e:
        logger.error(f"Database query failed: {e}")
        return []
