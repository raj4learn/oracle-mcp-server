# Relative Path: db_data_extractor\standard\schema.py
"""
Schema Explorer Module

This module provides tools for exploring Oracle database schemas and objects,
including functions to list schemas, tables, packages, procedures, and other objects.
"""

from .connection import OracleConnection
import os
import logging
from typing import Optional, List
from .db_models.db_models import SchemaObjectResponse, DependencyResponse

# from ..utils.log_utils import log_entry_exit
# from ..utils.db_utils import run_db_query

# Get logger for this module
logger = logging.getLogger('db_data_extractor.standard.schema')
logger.info('Schema Explorer module loaded')

class SchemaExplorer:
    """
    Tools for exploring Oracle database schemas and their objects.
    """
    def get_db_connection(self) -> OracleConnection.connect:
        """
        Returns the current database connection.
        
        Returns:
            OracleConnection: The current database connection object
        """
        logger.debug("SchemaExplorer: get_db_connection - Oracle Connection")
        return OracleConnection(keep_alive=True).connect()
    
    def __init__(self, connection=None):
        """
        Initialize with an existing connection or create a new one.
        
        Args:
            connection (OracleConnection, optional): Existing connection to use
        """
        logger.debug("SchemaExplorer: init - Oracle Connection")
        # Use an existing connection or create a new one with keep_alive=True
        self.connection = connection or OracleConnection(keep_alive=True)

    # @log_entry_exit()
    def get_schemas(self, limit: int = 1) -> List[str]:
        """
        Get list of all schemas/users in the database. 
        based on the environment variable ORACLE_USERNAME
        This will return the schema that the user has access to.
        
        Args:
            limit (int, optional): Maximum number of schemas to return. If None, returns all schemas.
            
        Returns:
            List[str]: List of schema names
        """
        # Base query
        query = f"""
        SELECT username AS schema_name
        FROM all_users
        where username = '{os.getenv('ORACLE_USERNAME','SCOTT').upper()}'
        ORDER BY username
        """
        
        # Add row limiting if specified using Oracle 12c+ syntax
        if limit is not None:
            query = f""" {query} FETCH FIRST {limit} ROWS ONLY """

        try:
            # Use the connection with keep_alive=True to maintain it open after operation completes
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query)
                schemas = [row[0] for row in cursor.fetchall()]
                cursor.close()  # Close cursor but keep connection open
            logger.info(f"Schema Name: {schemas}")
            return schemas
        except Exception as e:
            logger.error(f"Error retrieving schemas: {str(e)}")
            return []

    # @log_entry_exit()
    def get_schema_objects(self, schema: str, object_type: str, part_of_object_name: Optional[str] = None, dynamicWhereClause: Optional[str] = None, limit: Optional[int] = 500) -> List[SchemaObjectResponse]:
        """
        Get all database objects of a specific type in a schema.
        
        Args:
            schema (str): Schema name, if None returns accessible objects
            object_type (str): Object type filter ('TABLE', 'PACKAGE', 'PACKAGE BODY', 'PROCEDURE', 'FUNCTION', etc)
            part_of_object_name (str, optional): Part of Object Name to filter objects.
            dynamicWhereClause (str, optional): Additional WHERE clause conditions for all_objects, 
                                                that can used by the to add additoinal fitler clause to fitler the data. 
                                                for example-1: "(object_name like '%<Part String of Object Name>%')" 
                                                for example-2: "(object_name like '%<Part String of Object Name>%' and status = 'VALID')"
                                                for example-3: "(object_name like '%<Part String of Object Name>%' or object_name like '%<Part String of Object Name>%')"
            limit (int, optional): Maximum number of objects to return. If None, returns all objects.

        Returns:
            list: List of dictionaries with object details
        """
        # Build the query with filters
        schema_filter = f" AND owner = '{schema.upper()}'" if schema else ""
        type_filter = f" AND object_type = '{object_type.upper()}'" if object_type else ""
        dynamicWhereClause = f" AND {dynamicWhereClause}" if dynamicWhereClause else ""
        part_of_object_name_filter = f" AND object_name LIKE '%{part_of_object_name.upper()}%'" if part_of_object_name else ""
        # Base query
        query = f"""
        SELECT owner, object_name, object_type, status, created, last_ddl_time
        FROM all_objects
        WHERE 1=1
        {schema_filter}
        {type_filter}
        {part_of_object_name_filter}
        {dynamicWhereClause}
        ORDER BY owner, object_type, object_name
        """
        
        # Add row limiting if specified using Oracle 12c+ syntax
        if limit is not None:
            query = f""" {query} FETCH FIRST {limit} ROWS ONLY """
        
        try:
            # Use connection with keep_alive=True
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                logger.info(f"Executing SQL query: {query}")
                cursor.execute(query)
                logger.info("Completion of SQL query.")
                result = [SchemaObjectResponse(
                    owner=row[0], 
                    object_name=row[1], 
                    object_type=row[2], 
                    status=row[3],
                    created=row[4],
                    last_ddl_time=row[5]
                ) for row in cursor.fetchall()]
                cursor.close()  # Close cursor but keep connection open
            logger.info("SQL query result collected.")
            return result
        except Exception as e:
            logger.error(f"Error retrieving schema objects: {str(e)}")
            return []
    
    # @log_entry_exit()
    def get_object_dependencies(self, owner: str, object_name: str, limit: int = 200, dynamicWhereClause: Optional[str] = None) -> List[DependencyResponse]:
        """
        Get dependencies for a specific database object. from all_dependencies db dictionary
        
        Args:
            owner (str): Schema/owner of the object
            object_name (str): Name of the object
            limit (int, optional): Maximum number of dependencies to return. If None, returns all dependencies.
            dynamicWhereClause (str, optional): Additional WHERE clause conditions for all_dependencies, 
                                                that can used by the to add additoinal fitler clause to fitler the data. 
                                                for example-1: "(name like '%<Part String of Object Name>%')" 
                                                for example-2: "(name like '%<Part String of Object Name>%' and referenced_name LIKE '%<Part String of Object Name>%')"
                                                for example-3: "(name like '%<Part String of Object Name>%' or name like '%<Part String of Object Name>%')"
            
        Returns:
            list: List of dictionaries with dependency details
        """
        dynamicWhereClause = f"AND {dynamicWhereClause}" if dynamicWhereClause else ""
        
        # Base query
        query = f"""
        SELECT d.owner, d.name, d.type, d.referenced_owner,
                d.referenced_name, d.referenced_type, d.dependency_type
        FROM all_dependencies d 
        WHERE d.owner = '{owner.upper()}'
        AND d.name = '{object_name.upper()}'
        {dynamicWhereClause}
        ORDER BY d.referenced_owner, d.referenced_name
        """
        
        # Add row limiting if specified using Oracle 12c+ syntax
        if limit is not None:
            query = f""" {query} FETCH FIRST {limit} ROWS ONLY """
            try:
                with self.get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(query)
                    
                    dependencies = [
                        DependencyResponse(
                            owner=row[0],
                            name=row[1],
                            type=row[2],
                            referenced_owner=row[3],
                            referenced_name=row[4],
                            referenced_type=row[5],
                            dependency_type=row[6]
                        )
                        for row in cursor.fetchall()
                    ]
                    cursor.close()  # Close cursor but keep connection open
                return dependencies
            except Exception as e:
                logger.error(f"Error in _run_query: {str(e)}")
                return []
        
    def collect_dependencies_tree(self, owner: str, name: str, direction: str = 'down', depth: int = 2, visited=None) -> list:
        """
        Recursively collects a dependency tree for a given object.
        Args:
            owner (str): Schema/owner of the object
            name (str): Name of the object
            direction (str): 'down' for what this depends on, 'up' for what depends on this
            depth (int): Max depth to traverse
            visited (set): Used to avoid cycles
        Returns:
            list: List/tree of dependencies
        """
        if visited is None:
            visited = set()
        key = (owner.upper(), name.upper(), direction)
        if key in visited or depth < 1:
            return []
        visited.add(key)
        results = []
        if direction == 'down':
            # What this object depends on
            dependencies = self.get_object_dependencies(owner, name, limit=100)
            for dep in dependencies:
                child = {
                    'owner': dep.referenced_owner,
                    'name': dep.referenced_name,
                    'type': dep.referenced_type,
                    'dependency_type': dep.dependency_type,
                    'children': self.collect_dependencies_tree(dep.referenced_owner, dep.referenced_name, direction, depth-1, visited)
                }
                results.append(child)
        elif direction == 'up':
            # What depends on this object
            # Reverse query: find objects where referenced_name = name
            dynamicWhereClause = f"referenced_owner = '{owner.upper()}' AND referenced_name = '{name.upper()}'"
            query = f"""
                SELECT d.owner, d.name, d.type, d.referenced_owner, d.referenced_name, d.referenced_type, d.dependency_type
                FROM all_dependencies d
                WHERE {dynamicWhereClause}
                ORDER BY d.owner, d.name
            """
            try:
                with self.get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(query)
                    rows = cursor.fetchall()
                    cursor.close()
                for row in rows:
                    child = {
                        'owner': row[0],
                        'name': row[1],
                        'type': row[2],
                        'dependency_type': row[6],
                        'children': self.collect_dependencies_tree(row[0], row[1], direction, depth-1, visited)
                    }
                    results.append(child)
            except Exception as e:
                logger.error(f"Error collecting upstream dependencies: {str(e)}")
        return results

    def get_object_usage_audit(self, owner: str, name: str) -> dict:
        """
        Retrieves audit/usage metadata for a DB object: last DDL, status, and optionally last analyzed/used.
        Args:
            owner (str): Schema/owner of the object
            name (str): Name of the object
        Returns:
            dict: Usage and audit information
        """
        info = {}
        # Get from all_objects
        try:
            query = f"""
                SELECT status, created, last_ddl_time, object_type FROM all_objects
                WHERE owner = '{owner.upper()}' AND object_name = '{name.upper()}'
            """
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query)
                row = cursor.fetchone()
                if row:
                    info['status'] = row[0]
                    info['created'] = row[1]
                    info['last_ddl_time'] = row[2]
                    info['object_type'] = row[3]
                cursor.close()
        except Exception as e:
            logger.error(f"Error fetching object usage/audit info: {str(e)}")
        
        # Optionally: add last analyzed for tables
        if info.get('object_type', '').upper() == 'TABLE':
            try:
                query = f"""
                    SELECT last_analyzed FROM all_tables
                    WHERE owner = '{owner.upper()}' AND table_name = '{name.upper()}'
                """
                with self.get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(query)
                    row = cursor.fetchone()
                    if row:
                        info['last_analyzed'] = row[0]
                    cursor.close()
            except Exception as e:
                logger.error(f"Error fetching last_analyzed: {str(e)}")
        return info

# End of File
