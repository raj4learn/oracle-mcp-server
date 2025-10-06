# Relative Path: db_data_extractor\standard\source.py
"""
Source Code Retriever Module

This module provides tools for retrieving source code of Oracle database objects
such as packages, procedures, functions, triggers, and types.
"""

from .connection import OracleConnection
import logging
from typing import Optional
from ..utils.log_utils import log_entry_exit

# Get logger for this module
logger = logging.getLogger('db_data_extractor.standard.source')
logger.info('Source Code Retriever module loaded')


class SourceCodeRetriever:
    """
    Tools for retrieving and analyzing source code from Oracle database objects.
    """
    
    def __init__(self, connection=None):
        """
        Initialize with an existing connection or create a new one.
        
        Args:
            connection (OracleConnection, optional): Existing connection to use
        """
        self.connection = connection or OracleConnection()
    
    @log_entry_exit()
    def get_source_code(self, owner:str, name:str, type:str, start_line_number: int = 0, limit: Optional[int] = None, dynamicWhereClause: Optional[str] = None) -> str:
        """
        Get the source code for a database object (package, procedure, function, etc.)
        
        Args:
            owner (str): Schema/owner of the object
            name (str): Name of the object
            type (str): Object type ('PACKAGE', 'PACKAGE BODY', 'PROCEDURE', 'FUNCTION', etc.)
            start_line_number (int, optional): Start line number for the source code. If None, returns all source code.
            limit (int, optional): Maximum number of lines to return. If None, returns all source code.
            dynamicWhereClause (str, optional): Additional WHERE clause conditions for all_source, 
                                                that can used by the to add additoinal fitler clause to fitler the data. 
                                                for example-1: "object_name like '%<Part String of Object Name>%'" / "nullable = 'Y'"
                                                for example-2: "object_name like '%<Part String of Object Name>%' and nullable = 'Y'"
        Returns:
            str: Source code as a string with line breaks
        """
    
        logger.debug(f'Retrieving source code for {type} {owner}.{name}')
        conn = self.connection.connect()
        
        # Initialize the where clauses
        where_start_line_number = ""
        where_limit = ""
        
        # Handle start line filtering
        if start_line_number is not None and start_line_number > 0:
            where_start_line_number = f" AND line >= {start_line_number} "
            
        # Handle limit by calculating end line if both parameters are provided
        if limit is not None and limit > 0:
            end_line = start_line_number + limit if start_line_number is not None else limit
            where_limit = f" AND line <= {end_line} "
        
        if dynamicWhereClause:
            where_limit = f" AND {dynamicWhereClause} "

        query = f"""
            SELECT text
            FROM all_source
            WHERE name = :name
            AND owner = :owner
            AND type = :type
            {where_start_line_number}
            {where_limit}
            ORDER BY line
        """
        
        with conn.cursor() as cursor:
            cursor.execute(query, {"name": name.upper(), "owner": owner.upper(), "type": type.upper()})
            source_lines = [r[0] for r in cursor.fetchall()]
        
        if not source_lines:
            logger.warning(f"No source code found for {type} {owner}.{name}")
            return f"No source code found for {type} {owner}.{name}"
            
        logger.debug(f'Retrieved {len(source_lines)} lines of source code for {type} {owner}.{name}')

        return "\n".join(source_lines)
        
    @log_entry_exit()
    def get_package_details(self, owner:str, package_name:str, start_line_number: int = 0, limit: Optional[int] = None):
        """
        Get full package details including specification, body, and contents.
        
        Args:
            owner (str): Schema/owner of the package
            package_name (str): Name of the package
            
        Returns:
            dict: Dictionary with package details
        """
        logger.info(f'Retrieving package details for {owner}.{package_name}')
        
        # Get package specification
        spec = self.get_source_code(owner, package_name, "PACKAGE", start_line_number, limit)
        
        # Get package body
        body = self.get_source_code(owner, package_name, "PACKAGE BODY", start_line_number, limit)
        
        # Get package contents (procedures and functions)
        conn = self.connection.connect()
        query = f"""
        SELECT object_name, overload, object_id, subprogram_id
        FROM all_procedures
        WHERE owner = '{owner.upper()}'
        AND object_name = '{package_name.upper()}'
        AND procedure_name IS NOT NULL
        ORDER BY subprogram_id
        """
        
        logger.debug(f'Executing SQL query: {query}')
        with conn.cursor() as cursor:
            cursor.execute(query)
            contents = [
                {
                    "name": row[0],
                    "overload": row[1],
                    "object_id": row[2],
                    "subprogram_id": row[3]
                }
                for row in cursor.fetchall()
            ]
        
        logger.debug(f'Retrieved {len(contents)} procedures/functions for package {owner}.{package_name}')
        
        return {
            "owner": owner,
            "package_name": package_name,
            "specification": spec,
            "body": body,
            "procedures_functions": contents
        }
        
    @log_entry_exit()
    def get_procedure_function_details(self, owner:str, name:str, type="PROCEDURE"):
        """
        Get details of a standalone procedure or function.
        
        Args:
            owner (str): Schema/owner of the procedure/function
            name (str): Name of the procedure/function
            type (str): Either 'PROCEDURE' or 'FUNCTION'
            
        Returns:
            dict: Dictionary with procedure/function details
        """
        logger.info(f'Retrieving {type.lower()} details for {owner}.{name}')
        conn = self.connection.connect()
        
        # Get source code
        source = self.get_source_code(owner, name, type)
        
        # Get arguments
        query = f"""
        SELECT argument_name, position, data_type, in_out, data_length, data_precision, data_scale
        FROM all_arguments
        WHERE object_name = '{name.upper()}'
        AND owner = '{owner.upper()}'
        ORDER BY position
        """
        
        logger.debug(f'Executing SQL query: {query}')
        with conn.cursor() as cursor:
            cursor.execute(query)
            arguments = [
                {
                    "name": row[0],
                    "position": row[1],
                    "data_type": row[2],
                    "in_out": row[3],
                    "data_length": row[4],
                    "data_precision": row[5],
                    "data_scale": row[6]
                }
                for row in cursor.fetchall()
            ]
        
        logger.debug(f'Retrieved {len(arguments)} arguments for {type.lower()} {owner}.{name}')
        
        return {
            "owner": owner,
            "name": name,
            "type": type,
            "source": source,
            "arguments": arguments
        }

# End of file        
