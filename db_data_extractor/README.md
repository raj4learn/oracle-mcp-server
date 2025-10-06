# Database Data Extractor

## Overview

This module contains utilities for extracting and working with Oracle database data. It provides a clean, modular interface for accessing various database components like schemas, tables, stored procedures, and other database objects.

## Structure

The package is organized following Domain-Driven Design (DDD) principles:

```text
db_data_extractor/
├── standard/      # Core database extraction functionality (formerly oracle_tools)
└── utils/         # Shared utility functions used across extractors
└── README.md      # This file
```

## Modules

### Standard

Contains the core functionality for extracting data from Oracle databases. This module provides classes for exploring schemas, tables, and retrieving database object information.

Key components:

- `connection.py`: Oracle database connection management
- `schema.py`: Schema exploration and metadata retrieval
- `table.py`: Table structure and data access
- `source.py`: Source code retrieval for database objects
- `data.py`: General data retrieval operations
- `db_logs.py`: Database logging functionality
- `diagnostics.py`: Diagnostic tools for troubleshooting

### Utils

Contains shared utilities and helper functions used across the database data extractor modules.

Key components:

- `utils/log_utils.py`: Logging utilities and decorators
- `utils/validation.py`: SQL validation and standardized error handling
- `utils/json_utils.py`: JSON-safe encoding utilities

## Usage

The modules can be imported as follows:

```python
# Standard database components
from db_data_extractor.standard.connection import OracleConnection
from db_data_extractor.standard.schema import SchemaExplorer
from db_data_extractor.standard.table import TableExplorer

# Utilities
from db_data_extractor.utils.log_utils import log_entry_exit
```

## Design Principles

This module follows SOLID principles and Domain-Driven Design:

- **Single Responsibility**: Each class has a single, well-defined responsibility
- **Open/Closed**: Components are open for extension but closed for modification
- **Liskov Substitution**: Subtypes can be used interchangeably with their parent types
- **Interface Segregation**: Classes expose only what clients need
- **Dependency Inversion**: High-level modules depend on abstractions, not details
- **Ubiquitous Language**: Consistent naming reflecting domain concepts
