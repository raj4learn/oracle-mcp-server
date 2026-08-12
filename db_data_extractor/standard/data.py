# Relative Path: db_data_extractor\standard\data.py
"""
Data Retriever Module

This module provides tools for retrieving and manipulating data from Oracle database tables,
including functions to query data with parameters, handle LOB data types, and format results.
"""

from .connection import OracleConnection
import logging
from ..utils.log_utils import log_entry_exit

# Get logger for this module
logger = logging.getLogger('db_data_extractor.standard.data')
logger.info('Data Retriever module loaded')


class DataRetriever:
    """
    Tools for retrieving and manipulating data from Oracle database tables.
    """
    
    def __init__(self, connection=None):
        """
        Initialize with an existing connection or create a new one.
        
        Args:
            connection (OracleConnection, optional): Existing connection to use
        """
        self.connection = connection or OracleConnection()
    
    @log_entry_exit()
    def get_table_data(self, owner, table_name, where_clause=None, order_by=None, limit=100):
        """
        Retrieve data from a table with optional filtering and sorting.
        
        Args:
            owner (str): Schema/owner of the table
            table_name (str): Name of the table
            where_clause (str, optional): WHERE condition without the 'WHERE' keyword
            order_by (str, optional): ORDER BY clause without the 'ORDER BY' keywords
            limit (int, optional): Maximum number of rows to retrieve, defaults to 100
            
        Returns:
            dict: Dictionary with column names and row data
        """
        logger.info(f'Retrieving data from table {owner}.{table_name}')
        conn = self.connection.connect()
        
        # Build the query with optional clauses
        where_sql = f"WHERE {where_clause}" if where_clause else ""
        order_sql = f"ORDER BY {order_by}" if order_by else ""
        
        query = f"""
        SELECT *
        FROM {owner}.{table_name}
        {where_sql}
        {order_sql}
        """
        
        # Add row limiting based on Oracle version/syntax
        if limit:
            query = f"{query} FETCH FIRST {limit} ROWS ONLY"
            
        logger.debug(f'Executing SQL query: {query}')
        try:
            cursor = conn.cursor()
            cursor.execute(query)
            
            # Get column names
            columns = [col[0] for col in cursor.description]
            
            # Get data rows
            rows = []
            for row in cursor.fetchall():
                row_data = {}
                for i, col_value in enumerate(row):
                    # Convert non-serializable types to strings
                    if hasattr(col_value, 'read'):  # For LOBs
                        col_value = "LOB data"
                    elif isinstance(col_value, bytes):
                        # Handle binary data by encoding as base64
                        import base64
                        try:
                            col_value = base64.b64encode(col_value).decode('ascii')
                        except Exception:
                            col_value = "[BINARY DATA]"
                    elif col_value is not None and not isinstance(col_value, (int, float, bool, str)):
                        # Convert other non-standard types to string
                        try:
                            col_value = str(col_value)
                        except Exception:
                            col_value = "[UNCONVERTIBLE DATA]"
                    row_data[columns[i]] = col_value
                rows.append(row_data)
                
            cursor.close()
            
            logger.debug(f'Retrieved {len(rows)} rows from {owner}.{table_name}')
            return {
                "owner": owner,
                "table_name": table_name,
                "columns": columns,
                "rows": rows,
                "row_count": len(rows),
                "query": query
            }
        except Exception as e:
            logger.error(f'Error retrieving data from {owner}.{table_name}: {str(e)}')
            return {"error": str(e), "query": query}
            
    @log_entry_exit()
    def execute_sql(self, sql_query, params=None, fetch_results=True):
        """
        Execute an arbitrary SQL query with optional parameters.
        
        Args:
            sql_query (str): SQL query to execute
            params (dict or list, optional): Bind parameters for the query
            fetch_results (bool, optional): Whether to fetch and return results
            
        Returns:
            dict: Dictionary with query results or execution status
        """
        logger.info(f'Executing SQL query: {sql_query[:100]}{"..." if len(sql_query) > 100 else ""}')
        conn = self.connection.connect()
        
        try:
            cursor = conn.cursor()
            cursor.execute(sql_query, params or {})
            
            result = {
                "query": sql_query,
                "success": True
            }
            
            if fetch_results and cursor.description:
                # Query returned results
                columns = [col[0] for col in cursor.description]
                rows = []
                
                for row in cursor.fetchall():
                    row_data = {}
                    for i, col_value in enumerate(row):
                        # Convert non-serializable types to strings
                        if hasattr(col_value, 'read'):  # For LOBs
                            col_value = "LOB data"
                        row_data[columns[i]] = col_value
                    rows.append(row_data)
                
                result["columns"] = columns
                result["rows"] = rows
                result["row_count"] = len(rows)
                logger.debug(f'Query returned {len(rows)} rows')
            else:
                # DML or DDL statement with no results
                result["rows_affected"] = cursor.rowcount
                logger.debug(f'SQL affected {cursor.rowcount} rows')
                if sql_query.strip().upper().startswith(("INSERT", "UPDATE", "DELETE")):
                    conn.commit()
                    logger.debug('Transaction committed')
            
            cursor.close()
            return result
            
        except Exception as e:
            logger.error(f'SQL execution error: {str(e)}')
            return {
                "query": sql_query,
                "success": False,
                "error": str(e)
            }

# End of file