# Relative Path: oracle_mcp\tools\db_operations.py
# Database operations tools
# This are common Oracle Meta data collection details, not related to Application.

import logging
from typing import Optional, List, Dict, Any, Union
from oracle_mcp.config import DEFAULT_SCHEMA, DEFAULT_QUERY_LIMIT, DEFAULT_LARGE_QUERY_LIMIT, DEFAULT_SOURCE_CODE_LIMIT
from db_data_extractor.utils.validation import validate_sql_query, validate_where_clause, standardized_error_handler, SQLValidationError, DatabaseOperationError
from db_data_extractor.utils.json_utils import sanitize_for_json
from oracle_mcp.tools.db_models_std import (
    SchemaListResponse, PackageResponse, PackageListResponse, ProcedureResponse, ProcedureListResponse,
    FunctionResponse, FunctionListResponse, TableResponse, TableListResponse, TableColumnResponse,
    TableConstraintResponse, TableIndexResponse, TableDetailsResponse, DependencyResponse, SqlQueryResponse,
    ObjectSourceResponse
)

# Import from the new db_data_extractor structure
from db_data_extractor.standard.connection import OracleConnection
from db_data_extractor.standard.schema import SchemaExplorer
from db_data_extractor.standard.table import TableExplorer
from db_data_extractor.standard.data import DataRetriever
from db_data_extractor.standard.source import SourceCodeRetriever
from db_data_extractor.utils.log_utils import log_entry_exit

# Configure logging
logger = logging.getLogger('oracle_mcp')

# Initialize the tool instances
connection = OracleConnection()
schema_explorer = SchemaExplorer()
table_explorer = TableExplorer()
data_retriever = DataRetriever()
source_retriever = SourceCodeRetriever()

def register_tools(mcp_app):
    """Register all database operation tools with the MCP application."""
    
    # Using centralized configuration value instead of hardcoded string

    @mcp_app.tool(name="list_schemas")
    def list_schemas() -> SchemaListResponse:
        """
        Retrieves all accessible database schemas/users.
        
        This tool provides a list of all schemas that the current user can access.
        The returned schema names can be used as input parameters for other database tools.
        
        Parameters:
            None
        
        Returns:
            SchemaListResponse: A Pydantic model containing:
                - schemas: List of accessible schema names
                - count: Total number of accessible schemas
        """
        logger.info("Tool-like function: list_schemas called")
        schemas = schema_explorer.get_schemas()
        logger.info(f"list_schema: Schemas: {schemas}")
        return SchemaListResponse(schemas=schemas, count=len(schemas))
    
    @mcp_app.tool(name="list_tables")
    @log_entry_exit('oracle_mcp')
    @standardized_error_handler
    def list_tables(schema: str = DEFAULT_SCHEMA, part_of_object_name: str = "", dynamicWhereClause: str = "", limit: int = DEFAULT_QUERY_LIMIT) -> Union[TableListResponse, Dict[str, Any]]:
        """
        Lists tables in the specified schema from Oracle's all_objects dictionary view.
        
        This operation is useful for getting a list of tables that the user can
        access, and for getting the names of the tables that the user can use
        with other operations.
        
        Parameters:
            schema (str): Schema name to list tables from.
                        Use the list_schemas tool to get available schemas.
            part_of_object_name (str, optional): Part of Object Name to filter tables.
            dynamicWhereClause (str, optional): Additional WHERE clause conditions for all_objects.
                                For example: "(object_name like '%<Part String of Object Name>%')"
            limit (int): Maximum number of tables to return.
            
        Returns:
            TableListResponse: A Pydantic model containing:
                - schema_name: The schema name that was queried
                - tables: A list of TableResponse objects with table details
                - count: The total number of tables returned
            Dict[str, Any]: Error response if validation fails or execution encounters an error
                    * status: Object status
                    * created: Object creation time
                    * last_ddl_time: Last modification time
                - count: Total number of tables returned
        """
        logger.info(f"Tool-like function: list_tables called with schema={schema}, part_of_object_name={part_of_object_name}, dynamicWhereClause={dynamicWhereClause}, limit={limit}")
        logger.info(f"Parameter types: schema={type(schema)}, part_of_object_name={type(part_of_object_name)}, dynamicWhereClause={type(dynamicWhereClause)}, limit={type(limit)}")
        
        # Convert empty strings to None for proper handling
        part_of_object_name = part_of_object_name if part_of_object_name else None
        dynamicWhereClause = dynamicWhereClause if dynamicWhereClause else None
        
        # Validate the dynamic WHERE clause if provided
        if dynamicWhereClause:
            is_valid, error_message = validate_where_clause(dynamicWhereClause)
            if not is_valid:
                logger.error(f"Invalid WHERE clause: {error_message}")
                raise SQLValidationError(f"WHERE clause validation failed: {error_message}")
        
        try:
            tables_raw = schema_explorer.get_schema_objects(schema=schema, object_type="TABLE", part_of_object_name=part_of_object_name, dynamicWhereClause=dynamicWhereClause, limit=limit)
            tables = [TableResponse(
                owner=t.owner,
                name=t.object_name,
                type=t.object_type,
                status=t.status,
                created=t.created,
                last_ddl_time=t.last_ddl_time
            ) for t in tables_raw]
            return TableListResponse(schema_name=schema, tables=tables, count=len(tables))
        except Exception as e:
            logger.error(f"Error listing tables: {str(e)}")
            raise DatabaseOperationError(f"Error listing tables: {str(e)}")
        
    @mcp_app.tool(name="list_packages")
    @log_entry_exit('oracle_mcp')
    @standardized_error_handler
    def list_packages(schema: str = DEFAULT_SCHEMA, part_of_object_name: str= "", dynamicWhereClause: str= "", limit: int = DEFAULT_QUERY_LIMIT) -> PackageListResponse:
        """
        Lists PL/SQL packages in the specified schema from Oracle's all_objects dictionary view.
        
        This tool retrieves package objects that the current user can access within the specified schema.
        The package names returned can be used as input parameters for other database tools,
        including dependency analysis tools.
        
        Parameters:
            schema (str): Schema name to list packages from. Default is "SCOTT".
                        Use the list_schemas tool to get available schemas.
            part_of_object_name (str, optional): Part of Object Name to filter packages.
            dynamicWhereClause (str, optional): Additional WHERE clause conditions to filter results.
                                            Example filters:
                                            - "(object_name like '%<Part String of Object Name>%')"
                                            - "(object_name like '%<Part String of Object Name>%' and referenced_name LIKE '%<Part String of Object Name>%')"
                                            - "(object_name like '%<Part String of Object Name>%' or object_name like '%<Part String of Object Name>%')"
            limit (int): Maximum number of packages to return. Default is 200.                                            
        
        Returns:
            PackageListResponse: A Pydantic model containing:
                - schema_name: Name of the queried schema
                - packages: List of PackageResponse objects with these properties:
                    * owner: Schema name
                    * name: Package name
                    * type: Object type (always "PACKAGE")
                    * status: Object status (VALID/INVALID)
                    * created: Object creation timestamp
                    * last_ddl_time: Last modification timestamp
                - count: Total number of packages returned
        """
        if isinstance(schema, dict) and 'schema' in schema:
            schema_name = schema['schema']
        else:
            schema_name = schema
        logger.info(f"Tool-like function: list_packages called with schema={schema_name}")
        packages_raw = schema_explorer.get_schema_objects(schema=schema_name, object_type="PACKAGE", part_of_object_name=part_of_object_name, dynamicWhereClause=dynamicWhereClause, limit=limit)
        packages = [PackageResponse(
            owner=p.owner,
            name=p.object_name,
            type=p.object_type,
            status=p.status,
            created=p.created,
            last_ddl_time=p.last_ddl_time
        ) for p in packages_raw]
        return PackageListResponse(schema_name=schema_name, packages=packages, count=len(packages))

    @mcp_app.tool(name="list_procedures")
    @log_entry_exit('oracle_mcp')
    @standardized_error_handler
    def list_procedures(schema: str = DEFAULT_SCHEMA, part_of_object_name: str = "", dynamicWhereClause: str = "", limit: int = DEFAULT_QUERY_LIMIT) -> ProcedureListResponse:
        """
        Lists PL/SQL procedures in the specified schema from Oracle's all_objects dictionary view.
        
        This tool retrieves procedure objects that the current user can access within the specified schema.
        The procedure names returned can be used as input parameters for other database tools,
        including dependency analysis tools.
        
        Parameters:
            schema (str): Schema name to list procedures from. Default is "SCOTT".
                        Use the list_schemas tool to get available schemas.
            part_of_object_name (str, optional): Part of Object Name to filter procedures.
            dynamicWhereClause (str, optional): Additional WHERE clause conditions to filter results.
                                            Example filters:
                                            - "(object_name like '%<Part String of Object Name>%')"
                                            - "(object_name like '%<Part String of Object Name>%' and referenced_name LIKE '%<Part String of Object Name>%')"
                                            - "(object_name like '%<Part String of Object Name>%' or object_name like '%<Part String of Object Name>%')"
            limit (int): Maximum number of procedures to return. Default is 200.
        
        Returns:
            ProcedureListResponse: A Pydantic model containing:
                - schema_name: Name of the queried schema
                - procedures: List of ProcedureResponse objects with these properties:
                    * owner: Schema name
                    * name: Procedure name
                    * type: Object type (always "PROCEDURE")
                    * status: Object status (VALID/INVALID)
                    * created: Object creation timestamp
                    * last_ddl_time: Last modification timestamp
                - count: Total number of procedures returned
                
        Note:
            When presenting results to users, use this format:
            {
                Object_type: "PROCEDURE",
                Object_name: "<procedure_name>"
            }
        """
        if isinstance(schema, dict) and 'schema' in schema:
            schema_name = schema['schema']
        else:
            schema_name = schema
        logger.info(f"Tool-like function: list_procedures called with schema={schema_name}, limit={limit}")
        procedures_raw = schema_explorer.get_schema_objects(schema_name, "PROCEDURE", part_of_object_name, dynamicWhereClause, limit)
        procedures = [ProcedureResponse(
            owner=p.owner,
            name=p.object_name,
            type=p.object_type,
            status=p.status,
            created=p.created,
            last_ddl_time=p.last_ddl_time
        ) for p in procedures_raw]
        return ProcedureListResponse(schema_name=schema_name, procedures=procedures, count=len(procedures))
    
    @mcp_app.tool(name="list_functions")
    @log_entry_exit('oracle_mcp')
    @standardized_error_handler
    def list_functions(schema: str = DEFAULT_SCHEMA, part_of_object_name: str = "", dynamicWhereClause: str = "", limit: int = DEFAULT_QUERY_LIMIT) -> FunctionListResponse:
        """
        Lists PL/SQL functions in the specified schema from Oracle's all_objects dictionary view.
        
        This tool retrieves function objects that the current user can access within the specified schema.
        The function names returned can be used as input parameters for other database tools,
        including dependency analysis tools.
        
        Parameters:
            schema (str): Schema name to list functions from. Default is "SCOTT".
                        Use the list_schemas tool to get available schemas.
            part_of_object_name (str, optional): Part of Object Name to filter functions.
            dynamicWhereClause (str, optional): Additional WHERE clause conditions to filter results.
                                            Example filters:
                                            - "(object_name like '%<Part String of Object Name>%')"
                                            - "(object_name like '%<Part String of Object Name>%' and referenced_name LIKE '%<Part String of Object Name>%')"
                                            - "(object_name like '%<Part String of Object Name>%' or object_name like '%<Part String of Object Name>%')"
            limit (int): Maximum number of functions to return. Default is 200.

        Returns:
            FunctionListResponse: A Pydantic model containing:
                - schema_name: Name of the queried schema
                - functions: List of FunctionResponse objects with these properties:
                    * owner: Schema name
                    * name: Function name
                    * type: Object type (always "FUNCTION")
                    * status: Object status (VALID/INVALID)
                    * created: Object creation timestamp
                    * last_ddl_time: Last modification timestamp
                - count: Total number of functions returned
        """
        if isinstance(schema, dict) and 'schema' in schema:
            schema_name = schema['schema']
        else:
            schema_name = schema
        logger.info(f"Tool-like function: list_functions called with schema={schema_name}, limit={limit}")
        functions_raw = schema_explorer.get_schema_objects(schema_name, "FUNCTION", part_of_object_name, dynamicWhereClause, limit)
        functions = [FunctionResponse(
            owner=f.owner,
            name=f.object_name,
            type=f.object_type,
            status=f.status,
            created=f.created,
            last_ddl_time=f.last_ddl_time
        ) for f in functions_raw]
        return FunctionListResponse(schema_name=schema_name, functions=functions, count=len(functions))
        
    ##############################################################################################################################

    @mcp_app.tool(name="get_object_source_code")
    @log_entry_exit('oracle_mcp')
    @standardized_error_handler
    def get_object_source_code(object_name: str, object_type: str, schema: str = DEFAULT_SCHEMA, start_line_number: int = 0, limit: int = DEFAULT_SOURCE_CODE_LIMIT, dynamicWhereClause: str = "") -> ObjectSourceResponse:
        """
        Retrieves the source code of a database object from Oracle's all_source dictionary view.
        
        This tool fetches the source code for various database object types including functions,
        packages, procedures, triggers, and types. For packages and types, both the specification
        and body are retrieved when available.
        
        Parameters:
            object_name (str): Name of the database object to retrieve source code for
            object_type (str): Type of the database object. Valid values include:
                            "FUNCTION", "JAVA SOURCE", "PACKAGE", "PROCEDURE", "TRIGGER", "TYPE"
            schema (str): Schema/owner of the object. Default is "SCOTT".
                        Use the list_schemas tool to get available schemas.
            start_line_number (int): Starting line number to retrieve from. Default is 0 (beginning).
            limit (int): Maximum number of lines to return. Default is 8000.
            dynamicWhereClause (str, optional): Additional WHERE clause conditions to filter results.
                                            Example filters:
                                            - "(object_name like '%<Part String of Object Name>%')"
                                            - "(object_name like '%<Part String of Object Name>%' and referenced_name LIKE '%<Part String of Object Name>%')"
                                            - "(object_name like '%<Part String of Object Name>%' or object_name like '%<Part String of Object Name>%')"
        
        Returns:
            ObjectSourceResponse: A Pydantic model containing:
                - schema_name: Schema/owner of the object
                - object_name: Name of the database object
                - object_type: Type of the database object
                - source: Source code of the object specification
                - body: Source code of the object body (only for PACKAGE and TYPE objects)
        """

        if isinstance(schema, dict) and 'schema' in schema:
            schema_name = schema['schema']
        else:
            schema_name = schema
        logger.info(f"Tool-like function: get_object_source_code called with schema={schema_name}, object_name={object_name}, object_type={object_type}")
        
        if (object_type.upper() == "PACKAGE" or object_type.upper() == "TYPE"):
            source = source_retriever.get_source_code(schema_name, object_name, object_type, start_line_number, limit, dynamicWhereClause)
            body = source_retriever.get_source_code(schema_name, object_name, object_type + " BODY", start_line_number, limit, dynamicWhereClause)
        else:
            source = source_retriever.get_source_code(schema_name, object_name, object_type, start_line_number, limit, dynamicWhereClause)
            body = ""
        
        return ObjectSourceResponse(schema_name=schema_name, object_name=object_name, object_type=object_type, source=source, body=body)
    
    ##############################################################################################################################
    @mcp_app.tool(name="get_table_basic_details")
    @log_entry_exit('oracle_mcp')
    @standardized_error_handler
    def get_table_basic_details(table_name: str, schema: str = DEFAULT_SCHEMA, limit: int = DEFAULT_QUERY_LIMIT) -> Union[TableListResponse, Dict[str, Any]]:
        """
        Retrieves detailed information about tables in the specified schema from Oracle's dictionary views.
        
        This tool queries the all_tables and ALL_TAB_COMMENTS dictionary views to get comprehensive
        information about tables (supports partial matches). If a specific table_name is provided, only that table's details
        are returned; otherwise, all tables in the schema (up to the limit) are returned.
        
        Parameters:
            schema (str): Schema name to list tables from. Default is "SCOTT".
                        Use the list_schemas tool to get available schemas.
            table_name (str): Specific table name to retrieve details for.
                                    If None, returns details for all tables in the schema.
                                    Example filters:
                                    - "(table_name like '%TABLE%')"

            limit (int): Maximum number of tables to return. Default is 500.

        Returns:
            TableListResponse: A Pydantic model containing:
                - schema_name: Name of the queried schema
                - tables: List of TableResponse objects with these properties:
                    * owner: Schema name
                    * name: Table name
                    * type: Table type
                    * status: Table status
                    * num_rows: Estimated number of rows
                    * blocks: Number of data blocks
                    * avg_row_len: Average row length in bytes
                    * last_analyzed: Last statistics collection date
                    * comments: Table description/comments
                - count: Total number of tables returned
        """
        if isinstance(schema, dict) and 'schema' in schema:
            schema_name = schema['schema']
        else:
            schema_name = schema
        logger.info(f"Tool-like function: get_table_basic_details called with schema={schema_name}, table_name={table_name}")
        
        try:
            tables_raw = table_explorer.get_tables(schema_name, table_name, limit)
            return tables_raw
        except Exception as e:
            logger.error(f"Error getting table details: {str(e)}")
            raise DatabaseOperationError(f"Error getting table details: {str(e)}")

    @mcp_app.tool(name="get_table_details_with_column_and_indexes")
    @log_entry_exit('oracle_mcp')
    def get_table_details_with_column_and_indexes(table_name: str = None, schema: str = DEFAULT_SCHEMA, limit: int = DEFAULT_QUERY_LIMIT, dynamicWhereClause: Optional[str] = None) -> TableDetailsResponse:
        """
        Retrieves comprehensive details about a specific table including columns, constraints, and indexes.
        
        This tool provides a complete view of a table's structure by combining information from
        multiple Oracle dictionary views. It returns column definitions, constraints (primary keys,
        foreign keys, etc.), and indexes defined on the table.
        
        Parameters:
            table_name (str): Name of the table to retrieve details for.
                            Required parameter.
            schema (str): Schema name that owns the table. Default is "SCOTT".
                        Use the list_schemas tool to get available schemas.
            limit (int): Maximum number of columns to return. Default is 500.
            dynamicWhereClause (str, optional): Additional WHERE clause conditions to filter column results.
                                            Example filters:
                                            - "(column_name like '%CREATED%')"
                                            - "(column_name like '%UPDATED%' and nullable = 'Y')"
        
        Returns:
            TableDetailsResponse: A Pydantic model containing:
                - schema_name: Schema/owner of the table
                - table_name: Name of the table
                - columns: List of column definitions with data types, constraints, etc.
                - constraints: List of table constraints (PK, FK, unique, check)
                - indexes: List of indexes defined on the table
        """
        if isinstance(schema, dict) and 'schema' in schema:
            schema_name = schema['schema']
        else:
            schema_name = schema

        logger.info(f"Tool-like function: get_table_details called with schema={schema_name}, table_name={table_name}")
        columns_raw = table_explorer.get_table_columns(schema_name, table_name, limit, dynamicWhereClause)
        constraints_raw = table_explorer.get_table_constraints(schema_name, table_name, limit)
        indexes_raw = table_explorer.get_table_indexes(schema_name, table_name, limit)
        columns = [TableColumnResponse(
            column_name=c.column_name,
            data_type=c.data_type,
            comments=c.comments,
            nullable=c.nullable,
            default_value=c.default_value,
            data_length=c.data_length,
            data_precision=c.data_precision,
            data_scale=c.data_scale,
            column_id=c.column_id,
            default_length=c.default_length,
            data_default=c.data_default
        ) for c in columns_raw]
        constraints = [TableConstraintResponse(
            constraint_name=con.constraint_name,
            constraint_type=con.constraint_type,
            status=con.status,
            validated=con.validated,
            generated=con.generated,
            deferrable=con.deferrable,
            deferred=con.deferred,
            search_condition=con.search_condition,
            r_owner=con.r_owner,
            delete_rule=con.delete_rule
        ) for con in constraints_raw]
        indexes = [TableIndexResponse(
            index_name=idx.index_name,
            index_type=idx.index_type,
            uniqueness=idx.uniqueness,
            status=idx.status,
            tablespace_name=idx.tablespace_name,
            logging=idx.logging,
            degree=idx.degree,
            columns=idx.columns
        ) for idx in indexes_raw]
        return TableDetailsResponse(schema_name=schema_name, table_name=table_name, columns=columns, constraints=constraints, indexes=indexes)
    
    @mcp_app.tool(name="get_table_columns")
    @log_entry_exit('oracle_mcp')
    def get_table_columns(table_name: str, schema: str = DEFAULT_SCHEMA, limit: int = DEFAULT_QUERY_LIMIT, dynamicWhereClause: Optional[str] = None) -> List[TableColumnResponse]:
        """
        Retrieves detailed information about all columns in a specific table.
        
        This tool queries the all_tab_columns and ALL_COL_COMMENTS dictionary views to get
        comprehensive information about each column in the specified table, including data types,
        constraints, and comments.
        
        Parameters:
            table_name (str): Name of the table to retrieve columns for
            schema (str): Schema/owner of the table. Default is "SCOTT".
                        Use the list_schemas tool to get available schemas.
            limit (int): Maximum number of columns to return. Default is 500.
            dynamicWhereClause (str, optional): Additional WHERE clause conditions to filter results.
                                            Example filters:
                                            - "(column_name like '%CREATED%')"
                                            - "(column_name like '%UPDATED%' and nullable = 'Y')"
                                            - "(column_name like '%UPDATED%' or column_name like '%MODIFIED%')"
            
        Returns:
            List[TableColumnResponse]: A list of column definitions, each containing:
                - column_name: Name of the column
                - data_type: SQL data type (VARCHAR2, NUMBER, DATE, etc.)
                - nullable: Whether the column allows NULL values (Y/N)
                - default_value: Default value if specified
                - data_length: Maximum length for character columns
                - data_precision: Precision for numeric columns
                - data_scale: Scale for numeric columns
                - column_id: Position of the column in the table
                - default_length: Length of the default value expression
                - data_default: Full default value expression
                - comments: Column description/comments
        """
        logger.info(f"Tool-like function: get_table_columns called with schema={schema}, table_name={table_name}")
        return table_explorer.get_table_columns(schema, table_name, limit, dynamicWhereClause)

    @mcp_app.tool(name="get_table_constraints")
    @log_entry_exit('oracle_mcp')
    def get_table_constraints(table_name: str, schema: str = DEFAULT_SCHEMA, limit: int = DEFAULT_LARGE_QUERY_LIMIT) -> List[TableConstraintResponse]:
        """
        Retrieves all constraints defined on a specific table.
        
        This tool queries the all_constraints dictionary view to get information about
        primary keys, foreign keys, unique constraints, and check constraints defined
        on the specified table.
        
        Parameters:
            table_name (str): Name of the table to retrieve constraints for
            schema (str): Schema/owner of the table. Default is "SCOTT".
                        Use the list_schemas tool to get available schemas.
            limit (int): Maximum number of constraints to return. Default is 1000.
            
        Returns:
            List[TableConstraintResponse]: A list of constraint definitions, each containing:
                - constraint_name: Name of the constraint
                - constraint_type: Type of constraint (P=Primary Key, R=Foreign Key, U=Unique, C=Check)
                - status: Status of the constraint (ENABLED/DISABLED)
                - validated: Whether the constraint is validated (VALIDATED/NOT VALIDATED)
                - generated: Whether the constraint was system-generated
                - deferrable: Whether the constraint is deferrable
                - deferred: Whether the constraint is initially deferred
                - search_condition: Condition for check constraints
                - r_owner: Referenced schema for foreign keys
                - delete_rule: Delete rule for foreign keys (CASCADE, SET NULL, etc.)
        """
        logger.info(f"Tool-like function: get_table_constraints called with schema={schema}, table_name={table_name}")
        return table_explorer.get_table_constraints(schema, table_name, limit)

    @mcp_app.tool(name="get_table_indexes")
    @log_entry_exit('oracle_mcp')
    def get_table_indexes(table_name: str, schema: str = DEFAULT_SCHEMA, limit: int = DEFAULT_QUERY_LIMIT) -> List[TableIndexResponse]:
        """
        Retrieves all indexes defined on a specific table.
        
        This tool queries the all_indexes and all_ind_columns dictionary views to get
        comprehensive information about indexes defined on the specified table,
        including their types, uniqueness, and the columns they cover.
        
        Parameters:
            table_name (str): Name of the table to retrieve indexes for
            schema (str): Schema/owner of the table. Default is "SCOTT".
                        Use the list_schemas tool to get available schemas.
            limit (int): Maximum number of indexes to return. Default is 250.
            
        Returns:
            List[TableIndexResponse]: A list of index definitions, each containing:
                - index_name: Name of the index
                - index_type: Type of index (NORMAL, BITMAP, FUNCTION-BASED, etc.)
                - uniqueness: Whether the index enforces uniqueness (UNIQUE/NONUNIQUE)
                - status: Status of the index (VALID/INVALID)
                - tablespace_name: Tablespace where the index is stored
                - logging: Whether index operations are logged
                - degree: Degree of parallelism
                - columns: List of columns in the index, each containing:
                    * column_name: Name of the indexed column
                    * column_position: Position of the column in the index
                    * descend: Sort direction (ASC/DESC)
        """
        logger.info(f'TableExplorer.get_table_indexes called for {schema}.{table_name}')
        return table_explorer.get_table_indexes(schema, table_name, limit)

    ##############################################################################################################################
    
    @mcp_app.tool(name="get_object_dependencies")
    @log_entry_exit('oracle_mcp')
    def get_object_dependencies(name: str, owner: str = DEFAULT_SCHEMA, limit: int = DEFAULT_QUERY_LIMIT, dynamicWhereClause: Optional[str] = None) -> List[DependencyResponse]:
        """
        Retrieves direct dependencies for a specific database object.
        
        This tool queries the all_dependencies dictionary view to identify objects that
        the specified object depends on, and objects that depend on it. This helps in
        understanding the impact of changes to the object.
        
        Parameters:
            name (str): Name of the database object to analyze dependencies for
            owner (str): Schema/owner of the object. Default is "SCOTT".
                        Use the list_schemas tool to get available schemas.
            limit (int): Maximum number of dependencies to return. Default is 250.
            dynamicWhereClause (str, optional): Additional WHERE clause conditions to filter results.
                                            Example filters:
                                            - "(name like '%<Part String of Object Name>%')"
                                            - "(name like '%<Part String of Object Name>%' and referenced_name LIKE '%<Part String of Object Name>%')"
                                            - "(name like '%<Part String of Object Name>%' or name like '%<Part String of Object Name>%')"
            
        Returns:
            List[DependencyResponse]: A list of dependency relationships, each containing details about
                                    the dependent object and the referenced object, including their
                                    names, types, and the nature of the dependency.
        """
        logger.info(f"Tool-like function: get_object_dependencies called with owner={owner}, name={name}")
        return schema_explorer.get_object_dependencies(owner, name, limit, dynamicWhereClause)

    ##############################################################################################################################

    @mcp_app.tool(name="dependency_impact_analysis")
    @log_entry_exit('oracle_mcp')
    def dependency_impact_analysis(name: str, owner: str = DEFAULT_SCHEMA, depth: int = 2) -> dict:
        """
        Performs a comprehensive dependency impact analysis for a database object.
        
        This tool analyzes both upstream and downstream dependencies to create a complete
        dependency tree for the specified object. It recursively traverses the dependency
        chain up to the specified depth, showing both what the object depends on and what
        depends on it.
        
        Parameters:
            name (str): Name of the database object to analyze
            owner (str): Schema/owner of the object. Default is "SCOTT".
                        Use the list_schemas tool to get available schemas.
            depth (int): Maximum depth to traverse in the dependency tree. Default is 2.
                        Higher values provide more comprehensive analysis but may be slower.

        Returns:
            dict: A dictionary containing two keys:
                - 'depends_on': Tree structure of objects that this object depends on
                - 'depended_on_by': Tree structure of objects that depend on this object
        """
        logger.info(f"Dependency Impact Analysis for {owner}.{name} depth={depth}")
        # Downstream (what this object depends on)
        depends_on = schema_explorer.collect_dependencies_tree(owner, name, direction='down', depth=depth)
        # Upstream (what depends on this object)
        depended_on_by = schema_explorer.collect_dependencies_tree(owner, name, direction='up', depth=depth)
        return { 'depends_on': depends_on, 'depended_on_by': depended_on_by }

    @mcp_app.tool(name="get_object_usage_audit")
    @log_entry_exit('oracle_mcp')
    def get_object_usage_audit(name: str, owner: str = DEFAULT_SCHEMA) -> dict:
        """
        Retrieves audit and usage metadata for a database object.
        
        This tool provides important metadata about when and how a database object has been
        created, modified, and used. For tables, it includes statistics information; for
        procedures and functions, it includes execution statistics when available.
        
        Parameters:
            name (str): Name of the database object to retrieve audit info for
            owner (str): Schema/owner of the object. Default is "SCOTT".
                        Use the list_schemas tool to get available schemas.

        Returns:
            dict: A dictionary containing usage and audit information, which may include:
                - last_ddl_time: When the object was last modified
                - created: When the object was created
                - status: Current status (VALID/INVALID)
                - last_analyzed: When statistics were last gathered (for tables)
                - num_rows: Estimated row count (for tables)
                - last_executed: When the object was last executed (for procedures/functions)
                - execution_count: How many times it has been executed
        """
        logger.info(f"Object Usage/Audit for {owner}.{name}")
        usage_info = schema_explorer.get_object_usage_audit(owner, name)
        return usage_info

    @mcp_app.tool()
    @log_entry_exit('oracle_mcp')
    @standardized_error_handler
    def execute_sql(query: str) -> Union[SqlQueryResponse, Dict[str, Any]]:
        """
        Executes a SQL query against the Oracle database and returns the results.
        
        This tool allows direct execution of SQL statements, providing a flexible way to
        retrieve or manipulate data. It should be used when the predefined tools don't
        provide the specific information needed.
        
        Parameters:
            query (str): The complete SQL query to execute. This should be a valid Oracle SQL
                        statement including any necessary WHERE clauses, joins, etc.
            
        Returns:
            SqlQueryResponse: A Pydantic model containing:
                - query: The original SQL query that was executed
                - result: The query results as returned by the database
            Dict[str, Any]: Error response if validation fails or execution encounters an error
                
        Note:
            For security and performance reasons, complex queries should be carefully
            constructed and may be subject to execution time limits. Queries are validated
            for potential SQL injection attempts before execution.
        """
        logger.info(f"Tool-like function: execute_sql called with query={query}")
        
        # Validate the SQL query for potential injection or dangerous operations
        is_valid, error_message = validate_sql_query(query)
        if not is_valid:
            logger.warning(f"SQL validation failed: {error_message} for query: {query}")
            raise SQLValidationError(f"SQL validation failed: {error_message}")
        
        try:
            # Execute the validated query
            result = data_retriever.execute_sql(query)
            
            # Sanitize the result to ensure it can be serialized to JSON
            sanitized_result = sanitize_for_json(result)
            
            return SqlQueryResponse(query=query, result=sanitized_result)
        except Exception as e:
            logger.error(f"Error executing SQL query: {str(e)}")
            raise DatabaseOperationError(f"Error executing SQL query: {str(e)}")
    
    ##############################################################################################################################

# End of file
