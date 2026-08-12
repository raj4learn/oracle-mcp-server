# Relative Path: db_data_extractor\standard\db_models\db_models.py
from datetime import datetime
from pydantic import BaseModel
from typing import Optional, List, Union

# Pydantic response models
class SchemaNameResponse(BaseModel):
    schema_name: str

class SchemaObjectResponse(BaseModel):
    owner: str
    object_name: str
    object_type: str
    status: str
    created: Union[datetime, None] = None
    last_ddl_time: Union[datetime, None] = None

class DependencyResponse(BaseModel):
    owner: str
    name: str
    type: str
    referenced_owner: str
    referenced_name: str
    referenced_type: str
    dependency_type: str

# End of File
