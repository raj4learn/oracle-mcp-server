# Relative Path: db_data_extractor\standard\change_tracking.py
"""
Change Tracking Module

This module provides tools for tracking and analyzing changes to database objects,
which is crucial for triaging issues that might be related to recent modifications.
"""

from .connection import OracleConnection
from typing import Optional

class ChangeTracker:
    """
    Tools for tracking database changes.
    """
    
    def __init__(self, connection=None):
        """
        Initialize with an existing connection or create a new one.
        
        Args:
            connection (OracleConnection, optional): Existing connection to use
        """
        self.connection = connection or OracleConnection()
    
    def get_recent_ddl_changes(self, days=7, limit=None, dynamicWhereClause: Optional[str] = None):
        """
        Get recent DDL changes from the data dictionary.
        
        Args:
            days (int, optional): Number of days to look back
            limit (int, optional): Maximum number of changes to return. If None, returns all changes.
            dynamicWhereClause (str, optional): Additional WHERE clause conditions for all_objects, 
                                            that can used by the to add additional filter clause to filter the data. 
                                            for example-1: "(object_name like '%<Part String of Object Name>%')" 
                                            for example-2: "(object_name like '%<Part String of Object Name>%' and referenced_name LIKE '%<Part String of Object Name>%')"
                                            for example-3: "(object_name like '%<Part String of Object Name>%' or object_name like '%<Part String of Object Name>%')"
            
        Returns:
            dict: Dictionary with recent DDL changes
        """
        conn = self.connection.connect()
        
        dynamicWhereClause = f"AND {dynamicWhereClause}" if dynamicWhereClause else ""

        # Base query
        query = f"""
        SELECT do.owner, do.object_name, do.object_type, do.created, do.last_ddl_time,
               do.status, do.timestamp, us.name AS modified_by
        FROM all_objects do
        JOIN all_users us ON do.owner = us.username
        WHERE do.last_ddl_time > SYSDATE - {days}
        {dynamicWhereClause}
        ORDER BY do.last_ddl_time DESC
        """
        
        # Add row limiting if specified using Oracle 12c+ syntax
        if limit is not None:
            query = f"""
            {query}
            FETCH FIRST {limit} ROWS ONLY
            """
        
        try:
            cursor = conn.cursor()
            cursor.execute(query)
            
            changes = [
                {
                    "owner": row[0],
                    "object_name": row[1],
                    "object_type": row[2],
                    "created": row[3],
                    "last_ddl_time": row[4],
                    "status": row[5],
                    "timestamp": row[6],
                    "modified_by": row[7]
                }
                for row in cursor.fetchall()
            ]
            
            cursor.close()            # Group changes by type
            changes_by_type = {}
            for change in changes:
                obj_type = change.get("object_type")
                if obj_type not in changes_by_type:
                    changes_by_type[obj_type] = []
                changes_by_type[obj_type].append(change)
            
            # Group changes by owner
            changes_by_owner = {}
            for change in changes:
                owner = change.get("owner")
                if owner not in changes_by_owner:
                    changes_by_owner[owner] = []
                changes_by_owner[owner].append(change)
            
            return {
                "changes": changes,
                "changes_by_type": changes_by_type,
                "changes_by_owner": changes_by_owner,
                "total_changes": len(changes),
                "time_period": f"Last {days} days"
            }
        except Exception as e:
            return {"error": str(e)}
    
    def get_object_change_history(self, owner, object_name, object_type, limit=None):
        """
        Get the change history for a specific database object.
        
        Args:
            owner (str): Schema/owner of the object
            object_name (str): Name of the object
            object_type (str): Type of the object
            limit (int, optional): Maximum number of history records to return. If None, returns all records.
            
        Returns:
            dict: Dictionary with object change history
        """
        conn = self.connection.connect()
        
        # Try different approaches based on what's available in the database
        
        # First try DBA_AUDIT_OBJECT if available
        try:
            # Base query
            query = f"""
            SELECT username, timestamp, action_name, new_owner, new_name, obj_privilege
            FROM dba_audit_object
            WHERE owner = '{owner.upper()}'
            AND object_name = '{object_name.upper()}'
            ORDER BY timestamp DESC
            """
            
            # Add row limiting if specified
            if limit is not None:
                query = f"""
                SELECT * FROM (
                {query}
                ) WHERE ROWNUM <= {limit}
                """
            with conn.cursor() as cursor:
                cursor.execute(query)
                
                audit_history = [
                    {
                        "username": row[0],
                        "timestamp": row[1],
                        "action": row[2],
                        "new_owner": row[3],
                        "new_name": row[4],
                        "privilege": row[5]
                    }
                    for row in cursor.fetchall()
                ]

            return {
                "owner": owner,
                "object_name": object_name,
                "object_type": object_type,
                "audit_history": audit_history
            }
        except Exception:
            # If that fails, try to get information from all_objects
            try:
                query = f"""
                SELECT created, last_ddl_time, status, timestamp
                FROM all_objects
                WHERE owner = '{owner.upper()}'
                AND object_name = '{object_name.upper()}'
                AND object_type = '{object_type.upper()}'
                """
                with conn.cursor() as cursor:
                    cursor.execute(query)
                    row = cursor.fetchone()
                
                if row:
                    return {
                        "owner": owner,
                        "object_name": object_name,
                        "object_type": object_type,
                        "created": row[0],
                        "last_ddl_time": row[1],
                        "status": row[2],
                        "timestamp": row[3],
                        "note": "Limited change history available. Consider enabling object auditing."
                    }
                else:
                    return {
                        "owner": owner,
                        "object_name": object_name,
                        "object_type": object_type,
                        "error": "Object not found"
                    }
            except Exception as e2:
                return {
                    "owner": owner,
                    "object_name": object_name,
                    "object_type": object_type,
                    "error": f"Could not retrieve change history: {str(e2)}"
                }    
    
    def compare_execution_plans(self, sql_id, before_date, after_date):
        """
        Compare execution plans before and after a specific date.
        
        Args:
            sql_id (str): SQL ID to analyze
            before_date (str): Date in YYYY-MM-DD format for before comparison
            after_date (str): Date in YYYY-MM-DD format for after comparison
            
        Returns:
            dict: Dictionary with execution plan comparison
        """
        conn = self.connection.connect()
        
        # Try to get execution plans from AWR history if available
        try:
            # Get plans before the specified date
            before_query = f"""
            SELECT sql_id, plan_hash_value, timestamp, 
                   elapsed_time_per_exec, buffer_gets_per_exec, rows_processed_per_exec
            FROM dba_hist_sqlstat
            WHERE sql_id = '{sql_id}'
            AND TO_CHAR(begin_interval_time, 'YYYY-MM-DD') <= '{before_date}'
            ORDER BY begin_interval_time DESC
            FETCH FIRST 1 ROW ONLY
            """
            
            cursor = conn.cursor()
            cursor.execute(before_query)
            before_row = cursor.fetchone()
            
            # Get plans after the specified date
            after_query = f"""
            SELECT sql_id, plan_hash_value, timestamp, 
                   elapsed_time_per_exec, buffer_gets_per_exec, rows_processed_per_exec
            FROM dba_hist_sqlstat
            WHERE sql_id = '{sql_id}'
            AND TO_CHAR(begin_interval_time, 'YYYY-MM-DD') >= '{after_date}'
            ORDER BY begin_interval_time ASC
            FETCH FIRST 1 ROW ONLY
            """
            
            cursor.execute(after_query)
            after_row = cursor.fetchone()
            
            if before_row and after_row:
                # Get the detailed plan for each
                before_plan_query = f"""
                SELECT id, operation, options, object_name, 
                       cardinality, bytes, cost, temp_space
                FROM dba_hist_sql_plan
                WHERE sql_id = '{sql_id}'
                AND plan_hash_value = {before_row[1]}
                ORDER BY id
                """
                
                cursor.execute(before_plan_query)
                before_plan = [
                    {
                        "id": row[0],
                        "operation": row[1],
                        "options": row[2],
                        "object_name": row[3],
                        "cardinality": row[4],
                        "bytes": row[5],
                        "cost": row[6],
                        "temp_space": row[7]
                    }
                    for row in cursor.fetchall()
                ]
                
                after_plan_query = f"""
                SELECT id, operation, options, object_name, 
                       cardinality, bytes, cost, temp_space
                FROM dba_hist_sql_plan
                WHERE sql_id = '{sql_id}'
                AND plan_hash_value = {after_row[1]}
                ORDER BY id
                """
                
                cursor.execute(after_plan_query)
                after_plan = [
                    {
                        "id": row[0],
                        "operation": row[1],
                        "options": row[2],
                        "object_name": row[3],
                        "cardinality": row[4],
                        "bytes": row[5],
                        "cost": row[6],
                        "temp_space": row[7]
                    }
                    for row in cursor.fetchall()
                ]
                
                # Get the SQL text
                text_query = f"""
                SELECT sql_text 
                FROM dba_hist_sqltext 
                WHERE sql_id = '{sql_id}'
                """
                
                cursor.execute(text_query)
                text_row = cursor.fetchone()
                sql_text = text_row[0] if text_row else "SQL text not available"
                
                cursor.close()
                
                # Calculate performance differences
                perf_diff = {
                    "elapsed_time_change": (after_row[3] - before_row[3]) / before_row[3] * 100 if before_row[3] else None,
                    "buffer_gets_change": (after_row[4] - before_row[4]) / before_row[4] * 100 if before_row[4] else None,
                    "rows_processed_change": (after_row[5] - before_row[5]) / before_row[5] * 100 if before_row[5] else None
                }
                
                # Find plan differences
                plan_differences = []
                all_steps = set()
                
                before_plan_dict = {f"{step.get('id')}_{step.get('operation')}_{step.get('object_name')}": step for step in before_plan}
                after_plan_dict = {f"{step.get('id')}_{step.get('operation')}_{step.get('object_name')}": step for step in after_plan}
                
                all_steps.update(before_plan_dict.keys())
                all_steps.update(after_plan_dict.keys())
                
                for step_key in all_steps:
                    before_step = before_plan_dict.get(step_key)
                    after_step = after_plan_dict.get(step_key)
                    
                    if before_step and after_step:
                        # Step exists in both plans, check for differences
                        if before_step.get("cost") != after_step.get("cost") or before_step.get("cardinality") != after_step.get("cardinality"):
                            plan_differences.append({
                                "step": step_key,
                                "before": before_step,
                                "after": after_step,
                                "cost_change": (after_step.get("cost") - before_step.get("cost")) / before_step.get("cost") * 100 if before_step.get("cost") else None,
                                "cardinality_change": (after_step.get("cardinality") - before_step.get("cardinality")) / before_step.get("cardinality") * 100 if before_step.get("cardinality") else None
                            })
                    elif before_step:
                        # Step exists only in before plan
                        plan_differences.append({
                            "step": step_key,
                            "change_type": "removed",
                            "details": before_step
                        })
                    else:
                        # Step exists only in after plan
                        plan_differences.append({
                            "step": step_key,
                            "change_type": "added",
                            "details": after_step
                        })
                
                return {
                    "sql_id": sql_id,
                    "sql_text": sql_text,
                    "before_date": before_date,
                    "after_date": after_date,
                    "before_plan_hash": before_row[1],
                    "after_plan_hash": after_row[1],
                    "performance_differences": perf_diff,
                    "plan_differences": plan_differences,
                    "before_plan": before_plan,
                    "after_plan": after_plan
                }
            else:
                return {
                    "sql_id": sql_id,
                    "error": "Could not find execution plans for the specified dates",
                    "suggestion": "Try different date ranges or check if the SQL ID exists in the AWR history"
                }
        except Exception as e:
            return {
                "sql_id": sql_id,
                "error": f"Could not compare execution plans: {str(e)}",
                "suggestion": "Check if you have access to AWR history views or try using SQL monitoring reports"
            }

# End of the file
