# Relative Path: oracle_mcp\tools\db_models_std.py
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field
from datetime import datetime

# --- Connection Models ---
class ConnectionStatusResponse(BaseModel):
    is_connected: bool = Field(..., description="True if the connection is active and valid")
    dsn: Optional[str] = Field(None, description="Data Source Name for the connection")
    username: Optional[str] = Field(None, description="Username used for the connection")
    thick_mode: Optional[bool] = Field(None, description="Whether thick mode is enabled")
    message: Optional[str] = Field(None, description="Additional status or info message")

class ConnectionErrorResponse(BaseModel):
    is_connected: bool = Field(default=False, description="Always False for errors")
    error: str = Field(..., description="Error message or exception details")
    dsn: Optional[str] = Field(None, description="Data Source Name for the attempted connection")
    username: Optional[str] = Field(None, description="Username used for the attempted connection")
    thick_mode: Optional[bool] = Field(None, description="Whether thick mode was enabled")

# --- Schema Models ---
class SchemaListResponse(BaseModel):
    schemas: List[str]
    count: int

# --- Schema Models ---
class SchemaObjectResponse(BaseModel):
    owner: str
    object_name: str
    object_type: str
    status: str
    created: Union[datetime, None] = None
    last_ddl_time: Union[datetime, None] = None

# --- Package Models ---
class PackageResponse(BaseModel):
    owner: str
    name: str
    type: str
    status: str
    created: Union[datetime, None] = None
    last_ddl_time: Union[datetime, None] = None

class PackageListResponse(BaseModel):
    schema_name: str
    packages: List[PackageResponse]
    count: int

# --- Procedure Models ---
class ProcedureResponse(BaseModel):
    owner: str
    name: str
    type: str
    status: str
    created: Union[datetime, None] = None
    last_ddl_time: Union[datetime, None] = None

class ProcedureListResponse(BaseModel):
    schema_name: str
    procedures: List[ProcedureResponse]
    count: int

# --- Function Models ---
class FunctionResponse(BaseModel):
    owner: str
    name: str
    type: str
    status: str
    created: Union[datetime, None] = None
    last_ddl_time: Union[datetime, None] = None

class FunctionListResponse(BaseModel):
    schema_name: str
    functions: List[FunctionResponse]
    count: int

# --- Table Models ---
class TableResponse(BaseModel):
    owner: str
    name: str
    type: str
    status: Optional[str] = None
    created: Union[datetime, None] = None
    last_ddl_time: Union[datetime, None] = None
    comments: Optional[str] = None
    num_rows: Optional[int] = None
    blocks: Optional[int] = None
    avg_row_len: Optional[int] = None
    last_analyzed: Union[datetime, None] = None

class TableListResponse(BaseModel):
    schema_name: str
    tables: List[TableResponse]
    count: int

class TableColumnResponse(BaseModel):
    column_name: str
    data_type: Optional[str] = None
    nullable: Optional[str] = None
    default_value: Union[str, None] = None
    data_length: Optional[int] = None
    data_precision: Union[int, None] = None
    data_scale: Union[int, None] = None
    column_id: Optional[int] = None
    default_length: Union[int, None] = None
    data_default: Union[str, None] = None
    comments: Optional[str] = None

class TableConstraintResponse(BaseModel):
    constraint_name: str
    constraint_type: Optional[str] = None
    status: Optional[str] = None
    validated: Union[str, None] = None
    generated: Union[str, None] = None
    deferrable: Union[str, None] = None
    deferred: Union[str, None] = None
    search_condition: Union[str, None] = None
    r_owner: Union[str, None] = None
    delete_rule: Union[str, None] = None

class TableIndexColumnResponse(BaseModel):
    column_name: str
    column_position: Optional[int] = None
    descend: Optional[str] = None

class TableIndexResponse(BaseModel):
    index_name: str
    index_type: Optional[str] = None
    uniqueness: Optional[str] = None
    status: Optional[str] = None
    tablespace_name: Optional[str] = None
    logging: Optional[str] = None
    degree: Optional[int] = None
    columns: List[TableIndexColumnResponse] = Field(default_factory=list)


class TableDetailsResponse(BaseModel):
    schema_name: str
    table_name: str
    columns: List[TableColumnResponse]
    constraints: List[TableConstraintResponse]
    indexes: List[TableIndexResponse]

# --- Package Source ---
class ObjectSourceResponse(BaseModel):
    schema_name: str
    object_name: str
    object_type: str
    source: Optional[str] = None
    body: Optional[str] = None

# --- SQL Query ---
class SqlQueryResponse(BaseModel):
    query: str
    result: Dict[str, Any]

# -- Dependency Response ---
class DependencyResponse(BaseModel):
    owner: str
    name: str
    type: str
    referenced_owner: Optional[str] = None
    referenced_name: Optional[str] = None
    referenced_type: Optional[str] = None
    dependency_type: Optional[str] = None
