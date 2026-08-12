# Relative Path: db_data_extractor\standard\table.py
"""
Table Explorer Module

This module provides tools for exploring Oracle database tables, including
structure, columns, constraints, indexes, and other table-related metadata.
"""

from .connection import OracleConnection
import logging
from typing import Optional
from ..utils.log_utils import log_entry_exit
from oracle_mcp.tools.db_models_std import TableListResponse, TableResponse, TableColumnResponse, TableConstraintResponse, TableIndexResponse, TableIndexColumnResponse

# Get logger for this module
logger = logging.getLogger('db_data_extractor.standard.table')
logger.info('Table Explorer module loaded')


class TableExplorer:
    """
    Tools for exploring and analyzing Oracle database tables.
    """
    
    def __init__(self, connection=None):
        """
        Initialize with an existing connection or create a new one.
        
        Args:
            connection (OracleConnection, optional): Existing connection to use
        """
        logger.info('Initializing TableExplorer')
        self.connection = connection or OracleConnection()
        logger.debug('TableExplorer initialized with connection')
    
    @log_entry_exit()
    def get_tables(self, schema: str, table_name: str, limit: int = 200) -> TableListResponse:
        """
        Get all tables in the specified schema, and it get the tables list from oracle all_tables as t, ALL_TAB_COMMENTS as c dba dictionary
        
        Args:
            schema str: Schema name, if None returns accessible tables
            table_name str: Table name, it return like search of the table name given
            limit int: Maximum number of rows to return. If None, returns all rows.

        Returns:
            TableListResponse: Pydantic model with schema_name, table name, columns, constraints, and indexes
                schema_name: Schema name
                tables: List of tables
                count: Number of tables
            TableResponse: Pydantic model with table details
                owner: Schema name
                name: Table name
                type: Table type
                status: Table status
                num_rows: Number of rows
                blocks: Number of blocks
                avg_row_len: Average row length
                last_analyzed: Last analyzed date
                comments: Table comments
        """
        logger.info(f'TableExplorer.get_tables called with schema={schema}')
        conn = self.connection.connect()
        
        schema_filter = f"AND t.owner = '{schema.upper()}'" if schema else ""
        table_name_filter = f"AND t.table_name like '%{table_name.upper()}%'" if table_name else ""
        
        # Base query
        query = f"""
        SELECT t.owner, t.table_name, t.tablespace_name, t.status, t.num_rows, 
            t.blocks, t.avg_row_len, t.last_analyzed, c.comments
        FROM all_tables t, ALL_TAB_COMMENTS c
        WHERE 1=1
        AND t.owner = c.owner
        AND t.table_name = c.table_name
        {schema_filter}
        {table_name_filter}
        ORDER BY t.owner, t.table_name
        """
        
        # Add row limiting if specified using Oracle 12c+ syntax
        if limit is not None:
            query = f"""
            {query}
            FETCH FIRST {limit} ROWS ONLY
            """
        
        logger.debug(f'Executing SQL query: {query}')
        cursor = conn.cursor()
        cursor.execute(query)
        
        tables = [
            TableResponse(
                owner=row[0],
                name=row[1],
                type="TABLE",
                status=row[3],
                num_rows=row[4],
                blocks=row[5],
                avg_row_len=row[6],
                last_analyzed=row[7],
                comments=row[8]
            )
            for row in cursor.fetchall()
        ]
        
        cursor.close()
        logger.info(f'Retrieved {len(tables)} tables from schema {schema if schema else "ALL"}')
        logger.debug(f'Table list: {[f"{t.owner}.{t.name}" for t in tables[:5]]}{"..." if len(tables) > 5 else ""}')
        return TableListResponse(schema_name=schema, tables=tables, count=len(tables))
    
    @log_entry_exit()
    def get_table_columns(self, Schema: str, table_name: str, limit: int = 1000, dynamicWhereClause: Optional[str] = None) -> list[TableColumnResponse]:
        """
        Get all columns for a specific table. its get the columns list from oracle all_tab_columns tc, ALL_COL_COMMENTS cc dba dictionary
        
        Args:
            Schema (str): Schema/owner of the table
            table_name (str): Name of the table
            limit (int, optional): Maximum number of columns to return. If None, returns all columns.
            dynamicWhereClause (str, optional): Additional WHERE clause conditions for all_tab_columns, 
                                                that can used by the to add additoinal fitler clause to fitler the data. 
                                                for example-1: "(column_name like '%<Part String of Column Name>%')"
                                                for example-2: "(column_name like '%<Part String of Column Name>%' and nullable = 'Y')"
                                                for example-3: "(column_name like '%<Part String of Column Name>%' or column_name like '%<Part String of Column Name>%')"
            
        Returns:
            list[TableColumnResponse]: List of dictionaries with column details
                    column_name: Column name,
                    data_type: Data type,
                    nullable: Nullable,
                    default_value: Default value,
                    data_length: Data length,
                    data_precision: Data precision,
                    data_scale: Data scale,
                    column_id: Column id,
                    default_length: Default length,
                    data_default: Data default,
                    comments: Comments
        """
        logger.info(f'TableExplorer.get_table_columns called for {Schema}.{table_name}')
        conn = self.connection.connect()
        
        dynamicWhereClause = f"AND {dynamicWhereClause}" if dynamicWhereClause else ""

        # Base query
        query = f"""
        SELECT tc.column_name, tc.data_type, tc.data_length, tc.data_precision, tc.data_scale,
            tc.nullable, tc.column_id, tc.default_length, tc.data_default, cc.comments
        FROM all_tab_columns tc, ALL_COL_COMMENTS cc
        WHERE tc.table_name = '{table_name.upper()}'
        AND tc.owner = '{Schema.upper()}'
        AND tc.owner = cc.owner
        AND tc.table_name = cc.table_name
        AND tc.column_name = cc.column_name
        {dynamicWhereClause}
        ORDER BY tc.column_id
        """
        
        # Add row limiting if specified using Oracle 12c+ syntax
        if limit is not None:
            query = f"""
            {query}
            FETCH FIRST {limit} ROWS ONLY
            """
        
        logger.debug(f'Executing SQL query: {query}')
        cursor = conn.cursor()
        cursor.execute(query)
        
        columns = [TableColumnResponse(
            column_name=row[0],
            data_type=row[1],
            data_length=row[2],
            data_precision=row[3],
            data_scale=row[4],
            nullable=row[5],
            column_id=row[6],
            default_length=row[7],
            data_default=row[8],
            comments=row[9]
        ) for row in cursor.fetchall()
        ]
        
        cursor.close()
        logger.info(f'Retrieved {len(columns)} columns for table {Schema}.{table_name}')
        logger.debug(f'Column list: {[f"{c.column_name} ({c.data_type})" for c in columns[:5]]}{"..." if len(columns) > 5 else ""}')
        return columns
        
    @log_entry_exit()
    def get_table_constraints(self, Schema: str, table_name: str, limit: int = 1000) -> list[TableConstraintResponse]:
        """
        Get all constraints for a specific table. its get the constraints list from oracle all_constraints c dba dictionary
        
        Args:
            Schema (str): Schema/owner of the table
            table_name (str): Name of the table
            limit (int, optional): Maximum number of constraints to return. If None, returns all constraints.

        Returns:
            list[TableConstraintResponse]: List of dictionaries with constraint details
            constraint_name: Constraint name
            constraint_type: Constraint type
            status: Status
            validated: Validated
            generated: Generated
            deferrable: Deferrable
            deferred: Deferred
            search_condition: Search condition
            r_owner: R owner
            delete_rule: Delete rule
        """
        logger.info(f'TableExplorer.get_table_constraints called for {Schema}.{table_name}')
        conn = self.connection.connect()
        
        # Base query
        query = f"""
        SELECT c.constraint_name, c.constraint_type, c.status, c.validated,
            c.generated, c.deferrable, c.deferred, search_condition, r_owner, delete_rule
        FROM all_constraints c
        WHERE c.table_name = '{table_name.upper()}'
        AND c.owner = '{Schema.upper()}'
        ORDER BY c.constraint_name
        """
        # Add row limiting if specified using Oracle 12c+ syntax
        if limit is not None:
            query = f"""
            {query}
            FETCH FIRST {limit} ROWS ONLY
            """
        
        logger.debug(f'Executing SQL query: {query}')
        cursor = conn.cursor()
        cursor.execute(query)
        
        constraints = [TableConstraintResponse(
                constraint_name=row[0],
                constraint_type=row[1],
                status=row[2],
                validated=row[3],
                generated=row[4],
                deferrable=row[5],
                deferred=row[6],
                search_condition=row[7],
                r_owner=row[8],
                delete_rule=row[9]
            ) for row in cursor.fetchall()
        ]
        
        cursor.close()
        logger.info(f'Retrieved {len(constraints)} constraints for table {Schema}.{table_name}')
        logger.debug(f'Constraint list: {[f"{c.constraint_name} ({c.constraint_type})" for c in constraints[:5]]}{"..." if len(constraints) > 5 else ""}')
        return constraints
        
    @log_entry_exit()
    def get_table_indexes(self, Schema: str, table_name: str, limit: int = 250) -> list[TableIndexResponse]:
        """
        Get all indexes for a specific table.
        
        Args:
            Schema (str): Schema/owner of the table
            table_name (str): Name of the table
            limit (int, optional): Maximum number of indexes to return. If None, returns all indexes.            
        Returns:
            list[TableIndexResponse]: List of dictionaries with index details
                index_name: Index name
                index_type: Index type
                uniqueness: Uniqueness
                status: Status
                tablespace_name: Tablespace name
                logging: Logging
                degree: Degree
                columns: List of columns in the index
            TableIndexColumnResponse: Pydantic model with column details
                column_name: Column name
                column_position: Column position
                descend: Descend
        """
        logger.info(f'TableExplorer.get_table_indexes called for {Schema}.{table_name}')
        conn = self.connection.connect()
        
        # Base query
        query_table = """
        SELECT i.index_name, i.index_type, i.uniqueness, i.status,
            i.tablespace_name, i.logging, i.degree
        FROM all_indexes i
        WHERE i.table_name = :table_name
        AND i.table_owner = :Schema
        ORDER BY i.index_name
        """
        
        # Add row limiting if specified using Oracle 12c+ syntax
        if limit is not None:
            query_table = f"""
            {query_table}
            FETCH FIRST {limit} ROWS ONLY
            """
        
        logger.debug(f'Executing SQL query: {query_table}')

        with conn.cursor() as cursor:
            cursor.execute(query_table, {"table_name": table_name.upper(), "Schema": Schema.upper()})
            indexes = [
                TableIndexResponse(
                    index_name=row[0],
                    index_type=row[1],
                    uniqueness=row[2],
                    status=row[3],
                    tablespace_name=row[4],
                    logging=row[5],
                    degree=row[6]
                )
                for row in cursor.fetchall()
            ]
            # Get index columns for each index
            for index in indexes:
                index_name = index.index_name
                
                query_index_columns = """
                SELECT column_name, column_position, descend
                FROM all_ind_columns
                WHERE index_name = :index_name
                AND index_owner = :Schema
                ORDER BY column_position
                """
                cursor.execute(query_index_columns, {"index_name": index_name, "Schema": Schema.upper()})

                index.columns = [TableIndexColumnResponse(
                    column_name=row[0],
                    column_position=row[1],
                    descend=row[2]
                )for row in cursor.fetchall()
                ]
        
        logger.info(f'Retrieved {len(indexes)} indexes for table {Schema}.{table_name}')
        logger.debug(f'Index list: {[f"{i.index_name}" for i in indexes[:5]]}{"..." if len(indexes) > 5 else ""}')
        return indexes

# End of file