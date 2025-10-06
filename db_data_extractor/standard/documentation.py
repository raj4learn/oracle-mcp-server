# Relative Path: db_data_extractor\standard\documentation.py
"""
Documentation Module

This module provides tools for generating and retrieving documentation about database objects,
including usage patterns, common issues, and best practices.
"""

import os
import json
import datetime
from pathlib import Path
from .connection import OracleConnection
from typing import Optional

class DocumentationManager:
    """
    Tools for managing database object documentation.
    """
    
    def __init__(self, connection=None, doc_path=None):
        """
        Initialize with an existing connection or create a new one.
        
        Args:
            connection (OracleConnection, optional): Existing connection to use
            doc_path (str, optional): Path to documentation files, defaults to .windsurf/docs
        """
        self.connection = connection or OracleConnection()
        self.doc_path = doc_path or os.path.join(os.getcwd(), '.windsurf', 'docs')
        
        # Ensure documentation directory exists
        Path(self.doc_path).mkdir(parents=True, exist_ok=True)
    
    def get_table_usage_documentation(self, owner: str, table_name: str, dynamicWhereClause: Optional[str] = None):
        """
        Get documentation about how a table is used in the system.
        
        Args:
            owner (str): Schema/owner of the table
            table_name (str): Name of the table
            dynamicWhereClause (str, optional): Additional WHERE clause conditions, 
                                                that can used by the to add additoinal fitler clause to fitler the data. 
                                                for example-1: "(name like '%<Part String of Object Name>%')" 
                                                for example-2: "(name like '%<Part String of Object Name>%' and referenced_name LIKE '%<Part String of Object Name>%')"
                                                for example-3: "(name like '%<Part String of Object Name>%' or name like '%<Part String of Object Name>%')"
            
        Returns:
            dict: Table usage documentation if available
        """
        # First check for documentation file
        table_doc_path = os.path.join(self.doc_path, 'tables', f"{owner}_{table_name}.json")
        
        if os.path.exists(table_doc_path):
            with open(table_doc_path, 'r') as f:
                doc = json.load(f)
                return doc
        
        # If no file exists, try to generate basic documentation
        try:
            # Get basic table metadata
            conn = self.connection.connect()
            dynamicWhereClause = f"AND {dynamicWhereClause}" if dynamicWhereClause else ""
            
            # Get referencing tables (foreign keys)
            fk_query = f"""
            SELECT c.owner, c.table_name, c.constraint_name, cc.column_name
            FROM all_constraints c
            JOIN all_cons_columns cc ON c.constraint_name = cc.constraint_name AND c.owner = cc.owner
            WHERE c.constraint_type = 'R'
            AND c.r_owner = '{owner.upper()}'
            AND c.r_constraint_name IN (
                SELECT constraint_name 
                FROM all_constraints 
                WHERE owner = '{owner.upper()}' 
                AND table_name = '{table_name.upper()}'
                AND constraint_type IN ('P', 'U')
            )
            {dynamicWhereClause}
            """
            
            cursor = conn.cursor()
            cursor.execute(fk_query)
            
            referencing_tables = [
                {
                    "owner": row[0],
                    "table_name": row[1],
                    "constraint_name": row[2],
                    "column_name": row[3]
                }
                for row in cursor.fetchall()
            ]
            
            # Get procedures/functions that reference this table
            proc_query = f"""
            SELECT DISTINCT owner, name, type
            FROM all_source
            WHERE UPPER(text) LIKE '%{table_name.upper()}%'
            AND UPPER(text) NOT LIKE '%ALL_{table_name.upper()}%'
            {dynamicWhereClause}
            ORDER BY owner, name
            """
            
            cursor.execute(proc_query)
            
            referencing_procs = [
                {
                    "owner": row[0],
                    "name": row[1],
                    "type": row[2]
                }
                for row in cursor.fetchall()
            ]
            
            cursor.close()
            
            # Create basic documentation
            basic_doc = {
                "owner": owner,
                "table_name": table_name,
                "business_purpose": "No documentation available. Please add using set_table_documentation method.",
                "referencing_tables": referencing_tables,
                "referencing_procedures": referencing_procs,
                "note": "This is auto-generated documentation with limited information."
            }
            
            return basic_doc
            
        except Exception as e:
            return {
                "owner": owner,
                "table_name": table_name,
                "error": f"Could not generate documentation: {str(e)}",
                "suggestion": "Use set_table_documentation method to add documentation manually."
            }

    def set_table_documentation(self, owner, table_name, documentation):
        """
        Set or update documentation for a table.
        
        Args:
            owner (str): Schema/owner of the table
            table_name (str): Name of the table
            documentation (dict): Documentation details including:
                - business_purpose: Main purpose of the table
                - update_frequency: How often data is updated
                - primary_users: Who primarily uses this table
                - insert_trigger_events: Events that cause inserts
                - update_trigger_events: Events that cause updates
                - delete_trigger_events: Events that cause deletes
                - common_issues: Known issues and resolutions
            
        Returns:
            dict: Status of the operation
        """
        # Create tables directory if it doesn't exist
        tables_dir = os.path.join(self.doc_path, 'tables')
        Path(tables_dir).mkdir(parents=True, exist_ok=True)
        
        # Add metadata to the documentation
        full_doc = {
            "owner": owner,
            "table_name": table_name,
            "last_updated": str(datetime.datetime.now()),
            **documentation
        }
        
        # Save to file
        file_path = os.path.join(tables_dir, f"{owner}_{table_name}.json")
        try:
            with open(file_path, 'w') as f:
                json.dump(full_doc, f, indent=2)
                
            return {
                "status": "success",
                "message": f"Documentation saved for {owner}.{table_name}",
                "file_path": file_path
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to save documentation: {str(e)}"
            }
    
    def get_procedure_documentation(self, owner, package_name=None, procedure_name=None):
        """
        Get documentation about a stored procedure or function.
        
        Args:
            owner (str): Schema/owner of the procedure
            package_name (str, optional): Name of the package if procedure is in a package
            procedure_name (str): Name of the procedure or function
            
        Returns:
            dict: Procedure documentation if available
        """
        # Determine the file path based on whether it's a package procedure or standalone
        if package_name:
            doc_file = f"{owner}_{package_name}_{procedure_name}.json"
            subdir = 'package_procedures'
        else:
            doc_file = f"{owner}_{procedure_name}.json"
            subdir = 'procedures'
            
        proc_doc_path = os.path.join(self.doc_path, subdir, doc_file)
        
        # Check if documentation file exists
        if os.path.exists(proc_doc_path):
            with open(proc_doc_path, 'r') as f:
                doc = json.load(f)
                return doc
        
        # If no file exists, try to generate basic documentation
        try:
            conn = self.connection.connect()
            
            # Get procedure/function definition
            if package_name:
                query = f"""
                SELECT text
                FROM all_source
                WHERE owner = '{owner.upper()}'
                AND name = '{package_name.upper()}'
                AND type IN ('PACKAGE', 'PACKAGE BODY')
                AND UPPER(text) LIKE '%{procedure_name.upper()}%'
                ORDER BY line
                """
            else:
                query = f"""
                SELECT text
                FROM all_source
                WHERE owner = '{owner.upper()}'
                AND name = '{procedure_name.upper()}'
                AND type IN ('PROCEDURE', 'FUNCTION')
                ORDER BY line
                """
                
            cursor = conn.cursor()
            cursor.execute(query)
            source_lines = [row[0] for row in cursor.fetchall()]
            source_code = "".join(source_lines) if source_lines else "Source code not found"
            
            # Get procedure arguments
            args_query = f"""
            SELECT argument_name, position, data_type, in_out
            FROM all_arguments
            WHERE owner = '{owner.upper()}'
            AND object_name = '{package_name.upper() if package_name else procedure_name.upper()}'
            AND (package_name = '{package_name.upper() if package_name else "NULL"}' OR package_name IS NULL)
            ORDER BY position
            """
            
            cursor.execute(args_query)
            args = [
                {
                    "name": row[0],
                    "position": row[1],
                    "data_type": row[2],
                    "in_out": row[3]
                }
                for row in cursor.fetchall()
            ]
            
            # Try to find which tables this procedure affects
            tables_query = f"""
            SELECT DISTINCT t.owner, t.table_name
            FROM all_tables t
            WHERE EXISTS (
                SELECT 1
                FROM all_source s
                WHERE s.owner = '{owner.upper()}'
                AND s.name = '{package_name.upper() if package_name else procedure_name.upper()}'
                AND UPPER(s.text) LIKE '%' || t.table_name || '%'
            )
            ORDER BY t.owner, t.table_name
            """
            
            cursor.execute(tables_query)
            tables = [
                {
                    "owner": row[0],
                    "table_name": row[1]
                }
                for row in cursor.fetchall()
            ]
            
            cursor.close()
            
            # Create basic documentation
            basic_doc = {
                "owner": owner,
                "package_name": package_name,
                "procedure_name": procedure_name,
                "arguments": args,
                "related_tables": tables,
                "source_sample": source_code[:500] + ("..." if len(source_code) > 500 else ""),
                "business_purpose": "No documentation available. Please add using set_procedure_documentation method.",
                "note": "This is auto-generated documentation with limited information."
            }
            
            return basic_doc
            
        except Exception as e:
            return {
                "owner": owner,
                "package_name": package_name,
                "procedure_name": procedure_name,
                "error": f"Could not generate documentation: {str(e)}",
                "suggestion": "Use set_procedure_documentation method to add documentation manually."
            }
    
    def set_procedure_documentation(self, owner, procedure_name, documentation, package_name=None):
        """
        Set or update documentation for a procedure or function.
        
        Args:
            owner (str): Schema/owner of the procedure
            procedure_name (str): Name of the procedure or function
            documentation (dict): Documentation details including:
                - business_purpose: Main purpose of the procedure
                - execution_frequency: How often it's executed
                - tables_modified: Tables this procedure modifies
                - tables_queried: Tables this procedure queries
                - common_issues: Known issues and resolutions
            package_name (str, optional): Name of the package if procedure is in a package
            
        Returns:
            dict: Status of the operation
        """
        # Determine the subdirectory based on whether it's a package procedure or standalone
        if package_name:
            subdir = 'package_procedures'
            doc_file = f"{owner}_{package_name}_{procedure_name}.json"
        else:
            subdir = 'procedures'
            doc_file = f"{owner}_{procedure_name}.json"
            
        # Create directory if it doesn't exist
        proc_dir = os.path.join(self.doc_path, subdir)
        Path(proc_dir).mkdir(parents=True, exist_ok=True)
        
        # Add metadata to the documentation
        full_doc = {
            "owner": owner,
            "procedure_name": procedure_name,
            "package_name": package_name,
            "last_updated": str(datetime.datetime.now()),
            **documentation
        }
        
        # Save to file
        file_path = os.path.join(proc_dir, doc_file)
        try:
            with open(file_path, 'w') as f:
                json.dump(full_doc, f, indent=2)
                
            return {
                "status": "success",
                "message": f"Documentation saved for {owner}.{package_name + '.' if package_name else ''}{procedure_name}",
                "file_path": file_path
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to save documentation: {str(e)}"
            }
    
    def find_documentation(self, search_term):
        """
        Search for documentation containing specific terms.
        
        Args:
            search_term (str): Term to search for in documentation
            
        Returns:
            list: List of documentation entries matching the search term
        """
        results = []
        
        # Search through all documentation files
        for root, dirs, files in os.walk(self.doc_path):
            for file in files:
                if file.endswith('.json'):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r') as f:
                            doc = json.load(f)
                            
                            # Convert the entire doc to a string for searching
                            doc_str = json.dumps(doc).lower()
                            
                            if search_term.lower() in doc_str:
                                # Add a match with the file path and basic info
                                doc_type = "table" if "table_name" in doc else "procedure"
                                results.append({
                                    "type": doc_type,
                                    "file_path": file_path,
                                    "owner": doc.get("owner"),
                                    "name": doc.get("table_name") or doc.get("procedure_name"),
                                    "package": doc.get("package_name"),
                                    "last_updated": doc.get("last_updated")
                                })
                    except Exception:
                        # Skip files with errors
                        pass
        
        return results