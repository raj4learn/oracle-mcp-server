# Relative Path: db_data_extractor\standard\dataobject.py
"""
Oracle Data Object Module

This module provides specialized tools for working with Oracle data objects,
including views, materialized views, synonyms, and other database objects
that represent or reference data.
"""

from .connection import OracleConnection
from typing import Optional

class DataObjectExplorer:
    """
    Tools for exploring and analyzing Oracle data objects such as views,
    materialized views, sequences, and synonyms.
    """
    
    def __init__(self, connection=None):
        """
        Initialize with an existing connection or create a new one.
        
        Args:
            connection (OracleConnection, optional): Existing connection to use
        """
        self.connection = connection or OracleConnection()
    
    def get_views(self, schema=None, limit=None, dynamicWhereClause: Optional[str] = None):
        """
        Get all views in the specified schema.
        
        Args:
            schema (str, optional): Schema name, if None returns accessible views
            limit (int, optional): Maximum number of views to return. If None, returns all views.
            dynamicWhereClause (str, optional): Additional WHERE clause conditions, 
                                            that can used by the to add additoinal fitler clause to fitler the data. 
                                            for example-1: "(view_name like '%<Part String of Object Name>%')" 
                                            for example-2: "(view_name like '%<Part String of Object Name>%' and referenced_name LIKE '%<Part String of Object Name>%')"
                                            for example-3: "(view_name like '%<Part String of Object Name>%' or view_name like '%<Part String of Object Name>%')"
            
        Returns:
            list: List of dictionaries with view details
        """
        conn = self.connection.connect()
        
        schema_filter = f"AND owner = '{schema.upper()}'" if schema else ""
        dynamicWhereClause = f"AND {dynamicWhereClause}" if dynamicWhereClause else ""
        # Base query
        query = f"""
        SELECT owner, view_name, text_length, type_text, oid_text_length,
               view_type_owner, view_type, superview_name
        FROM all_views
        WHERE 1=1
        {schema_filter}
        {dynamicWhereClause}
        ORDER BY owner, view_name
        """
        
        # Add row limiting if specified using Oracle 12c+ syntax
        if limit is not None:
            query = f"""
            {query}
            FETCH FIRST {limit} ROWS ONLY
            """
        
        cursor = conn.cursor()
        cursor.execute(query)
        
        views = [
            {
                "owner": row[0],
                "name": row[1],
                "text_length": row[2],
                "type_text": row[3],
                "oid_text_length": row[4],
                "view_type_owner": row[5],
                "view_type": row[6],
                "superview_name": row[7]
            }
            for row in cursor.fetchall()
        ]
        
        cursor.close()
        return views
        
    def get_view_source(self, owner, view_name, dynamicWhereClause: Optional[str] = None):
        """
        Get the source definition of a view.
        
        Args:
            owner (str): Schema/owner of the view
            view_name (str): Name of the view
            dynamicWhereClause (str, optional): Additional WHERE clause conditions, 
                                            that can used by the to add additoinal fitler clause to fitler the data. 
                                            for example-1: "(view_name like '%<Part String of Object Name>%')" 
                                            for example-2: "(view_name like '%<Part String of Object Name>%' and referenced_name LIKE '%<Part String of Object Name>%')"
                                            for example-3: "(view_name like '%<Part String of Object Name>%' or view_name like '%<Part String of Object Name>%')"
            
        Returns:
            str: SQL definition of the view
        """
        conn = self.connection.connect()
            
        dynamicWhereClause = f"AND {dynamicWhereClause}" if dynamicWhereClause else ""
        query = f"""
        SELECT text
        FROM all_views
        WHERE view_name = '{view_name.upper()}'
        AND owner = '{owner.upper()}'
        {dynamicWhereClause}
        """
        
        cursor = conn.cursor()
        cursor.execute(query)
        row = cursor.fetchone()
        cursor.close()
        
        if not row:
            return f"No view found with name {owner}.{view_name}"
            
        return row[0]
    
    def get_materialized_views(self, schema=None, limit=None, dynamicWhereClause: Optional[str] = None):
        """
        Get all materialized views in the specified schema.
        
        Args:
            schema (str, optional): Schema name, if None returns accessible materialized views
            limit (int, optional): Maximum number of materialized views to return. If None, returns all materialized views.
            dynamicWhereClause (str, optional): Additional WHERE clause conditions, 
                                            that can used by the to add additoinal fitler clause to fitler the data. 
                                            for example-1: "(mview_name like '%<Part String of Object Name>%')" 
                                            for example-2: "(mview_name like '%<Part String of Object Name>%' and referenced_name LIKE '%<Part String of Object Name>%')"
                                            for example-3: "(mview_name like '%<Part String of Object Name>%' or mview_name like '%<Part String of Object Name>%')"

        Returns:
            list: List of dictionaries with materialized view details
        """
        conn = self.connection.connect()
        
        schema_filter = f"AND owner = '{schema.upper()}'" if schema else ""
        dynamicWhereClause = f"AND {dynamicWhereClause}" if dynamicWhereClause else ""
        
        # Base query
        query = f"""
        SELECT owner, mview_name, container_name, query, query_len,
               updatable, update_log, master_rollback_seg, last_refresh_date, refresh_method
        FROM all_mviews
        WHERE 1=1
        {schema_filter}
        {dynamicWhereClause}
        ORDER BY owner, mview_name
        """
        
        # Add row limiting if specified using Oracle 12c+ syntax
        if limit is not None:
            query = f"""
            {query}
            FETCH FIRST {limit} ROWS ONLY
            """
        
        cursor = conn.cursor()
        cursor.execute(query)
        
        mviews = [
            {
                "owner": row[0],
                "name": row[1],
                "container_name": row[2],
                "query_len": row[4],
                "updatable": row[5],
                "update_log": row[6],
                "master_rollback_seg": row[7],
                "last_refresh_date": row[8],
                "refresh_method": row[9]
            }
            for row in cursor.fetchall()
        ]
        
        cursor.close()
        return mviews
        
# End of the file
