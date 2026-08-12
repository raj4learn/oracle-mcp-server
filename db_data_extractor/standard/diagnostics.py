# Relative Path: db_data_extractor\standard\diagnostics.py
"""
Oracle Diagnostics Module

This module provides specialized tools for diagnosing and troubleshooting Oracle database issues,
including performance problems, lock contention, and error analysis.
"""

import logging
from .connection import OracleConnection
from typing import Optional

# Get logger for this module
logger = logging.getLogger('db_data_extractor.standard.diagnostics')
logger.info('Diagnostics module loaded')


class DiagnosticTools:
    """
    Tools for diagnosing Oracle database issues.
    """
    
    def __init__(self, connection=None):
        """
        Initialize with an existing connection or create a new one.
        
        Args:
            connection (OracleConnection, optional): Existing connection to use
        """
        self.connection = connection or OracleConnection()
        logger.debug('DiagnosticTools initialized')
    
    def analyze_session_waits(self, session_id=None, dynamicWhereClause: Optional[str] = None):
        """
        Analyze current session wait events to identify bottlenecks.
        
        Args:
            session_id (int, optional): Specific session ID to analyze. If None, analyzes all sessions.
            dynamicWhereClause (str, optional): Additional WHERE clause conditions, 
                                                that can used by the to add additoinal fitler clause to fitler the data. 
                                                for example-1: "(sid = 1)"
                                                for example-2: "(sid = 1 and username = 'SYSTEM')"
                                                for example-3: "(sid = 1 or username = 'SYSTEM')"
        Returns:
            dict: Dictionary with session wait analysis
        """
        conn = self.connection.connect()
        
        # Build query based on whether a specific session is provided
        session_filter = f"AND s.sid = {session_id}" if session_id else ""
        dynamicWhereClause = f"AND {dynamicWhereClause}" if dynamicWhereClause else ""
        
        query = f"""
        SELECT s.sid, s.serial#, s.username, s.status, s.machine, s.program,
               sw.event, sw.wait_time, sw.seconds_in_wait, sw.state
        FROM v$session s
        LEFT JOIN v$session_wait sw ON s.sid = sw.sid
        WHERE s.type = 'USER'
        {session_filter}
        {dynamicWhereClause}
        ORDER BY sw.seconds_in_wait DESC
        """
        
        cursor = conn.cursor()
        cursor.execute(query)
        
        waiting_sessions = [
            {
                "sid": row[0],
                "serial": row[1],
                "username": row[2],
                "status": row[3],
                "machine": row[4],
                "program": row[5],
                "wait_event": row[6],
                "wait_time": row[7],
                "seconds_in_wait": row[8],
                "wait_state": row[9]
            }
            for row in cursor.fetchall()
        ]
        
        cursor.close()
        
        # Group by wait event type
        wait_events = {}
        for session in waiting_sessions:
            event = session.get("wait_event")
            if event not in wait_events:
                wait_events[event] = []
            wait_events[event].append(session)
        
        return {
            "sessions": waiting_sessions,
            "wait_events": wait_events,
            "total_sessions": len(waiting_sessions)
        }
    
    def identify_blocking_sessions(self, dynamicWhereClause: Optional[str] = None):
        """
        Identify sessions that are blocking other sessions.
        
        Returns:
            dict: Dictionary with information about blocking sessions
        """
        conn = self.connection.connect()
        dynamicWhereClause = f"AND {dynamicWhereClause}" if dynamicWhereClause else ""
        
        query = """
        SELECT
            s1.sid blocking_sid,
            s1.serial# blocking_serial,
            s1.username blocking_user,
            s1.machine blocking_machine,
            s1.program blocking_program,
            s2.sid blocked_sid,
            s2.serial# blocked_serial,
            s2.username blocked_user,
            s2.machine blocked_machine,
            s2.program blocked_program,
            s2.wait_class blocked_wait_class,
            s2.seconds_in_wait blocked_seconds_waiting,
            lo.object_id locked_object_id,
            o.object_name locked_object
        FROM
            v$session s1
        JOIN
            v$session s2 ON s2.blocking_session = s1.sid
        LEFT JOIN
            v$locked_object lo ON s2.sid = lo.session_id
        LEFT JOIN
            all_objects o ON lo.object_id = o.object_id
        WHERE
            s1.sid != s2.sid
            {dynamicWhereClause}
        ORDER BY
            s2.seconds_in_wait DESC
        """
        
        cursor = conn.cursor()
        cursor.execute(query)
        
        blocking_sessions = [
            {
                "blocking": {
                    "sid": row[0],
                    "serial": row[1],
                    "username": row[2],
                    "machine": row[3],
                    "program": row[4]
                },
                "blocked": {
                    "sid": row[5],
                    "serial": row[6],
                    "username": row[7],
                    "machine": row[8],
                    "program": row[9],
                    "wait_class": row[10],
                    "seconds_waiting": row[11]
                },
                "locked_object": {
                    "id": row[12],
                    "name": row[13]
                }
            }
            for row in cursor.fetchall()
        ]
        
        cursor.close()
        
        # Group by blocker
        blockers = {}
        for block in blocking_sessions:
            blocker_sid = block["blocking"]["sid"]
            if blocker_sid not in blockers:
                blockers[blocker_sid] = {
                    "blocker_info": block["blocking"],
                    "blocked_sessions": []
                }
            blockers[blocker_sid]["blocked_sessions"].append(block["blocked"])
        
        return {
            "blocking_sessions": blocking_sessions,
            "blockers": blockers,
            "total_blockers": len(blockers),
            "total_blocked": len(blocking_sessions)
        }
    
    def get_sql_execution_plan(self, sql_id, dynamicWhereClause: Optional[str] = None):
        """
        Get the execution plan for a specific SQL statement.
        
        Args:
            sql_id (str): SQL ID to analyze
            dynamicWhereClause (str, optional): Additional WHERE clause conditions only for v$sqlarea, 
                                                that can used by the to add additoinal fitler clause to fitler the data. 
                                                for example-1: "(sql_id = '1234567890')"
                                                for example-2: "(sql_id = '1234567890' and sql_text like '%<Part String of Object Name>%')"
                                                for example-3: "(sql_id = '1234567890' or sql_text like '%<Part String of Object Name>%')"
            
        Returns:
            dict: Dictionary with execution plan details
        """
        conn = self.connection.connect()
        dynamicWhereClause = f"AND {dynamicWhereClause}" if dynamicWhereClause else ""        
        
        # Get SQL text
        text_query = f"""
        SELECT sql_text
        FROM v$sqlarea
        WHERE sql_id = '{sql_id}'
        {dynamicWhereClause}
        """
        
        cursor = conn.cursor()
        cursor.execute(text_query)
        
        row = cursor.fetchone()
        if not row:
            cursor.close()
            return {
                "sql_id": sql_id,
                "error": "SQL ID not found"
            }
        
        sql_text = row[0]
        
        # Get execution plan
        plan_query = f"""
        SELECT id, parent_id, operation, options, object_name,
            cardinality, bytes, cost, cpu_cost, io_cost
        FROM v$sql_plan
        WHERE sql_id = '{sql_id}'
        ORDER BY id
        """
        
        cursor.execute(plan_query)
        plan_steps = [
            {
                "id": row[0],
                "parent_id": row[1],
                "operation": row[2],
                "options": row[3],
                "object_name": row[4],
                "cardinality": row[5],
                "bytes": row[6],
                "cost": row[7],
                "cpu_cost": row[8],
                "io_cost": row[9]
            }
            for row in cursor.fetchall()
        ]
        
        # Get execution statistics if available
        stats_query = f"""
        SELECT sql_id, plan_hash_value, executions, elapsed_time, cpu_time,
            buffer_gets, disk_reads, rows_processed
        FROM v$sql 
        WHERE sql_id = '{sql_id}'
        ORDER BY last_active_time DESC
        """
        
        cursor.execute(stats_query)
        stats_row = cursor.fetchone()
        
        execution_stats = {}
        if stats_row:
            execution_stats = {
                "plan_hash_value": stats_row[1],
                "executions": stats_row[2],
                "elapsed_time": stats_row[3],
                "cpu_time": stats_row[4],
                "buffer_gets": stats_row[5],
                "disk_reads": stats_row[6],
                "rows_processed": stats_row[7],
                "elapsed_time_per_exec": stats_row[3] / stats_row[2] if stats_row[2] else 0,
                "buffer_gets_per_exec": stats_row[5] / stats_row[2] if stats_row[2] else 0,
                "disk_reads_per_exec": stats_row[6] / stats_row[2] if stats_row[2] else 0
            }
        
        cursor.close()
        
        return {
            "sql_id": sql_id,
            "sql_text": sql_text,
            "plan_steps": plan_steps,
            "execution_stats": execution_stats
        }
    
    def analyze_error_log(self, hours=24, error_code=None, limit=None):
        """
        Analyze database error logs to identify patterns or recurring issues.
        
        Args:
            hours (int, optional): Number of hours to look back in the logs
            error_code (str, optional): Specific error code to filter for
            limit (int, optional): Maximum number of error log entries to return. Default is 100 if not specified.
            
        Returns:
            dict: Dictionary with error log analysis
        """
        conn = self.connection.connect()
        
        error_filter = f"AND message_text LIKE '%{error_code}%'" if error_code else ""
        
        # Default limit to 100 if not specified
        row_limit = 100 if limit is None else limit
        
        try:
            # Try to get errors from the alert log
            query = f"""
            SELECT * FROM (
                SELECT originating_timestamp, message_text
                FROM X$DBGALERTEXT
                WHERE originating_timestamp > SYSTIMESTAMP - INTERVAL '{hours}' HOUR
                    AND message_text LIKE '%ORA-%'
                    {error_filter}
                ORDER BY originating_timestamp DESC
            ) FETCH FIRST {row_limit} ROWS ONLY
            """
            with conn.cursor() as cursor: 
                cursor.execute(query)

                alerts = [
                    {
                        "timestamp": row[0],
                        "message": row[1]
                    }
                    for row in cursor.fetchall()
                ]
            
            # Group errors by code
            error_summary = {}
            for alert in alerts:
                message = alert.get("message")
                # Extract ORA error code
                if "ORA-" in message:
                    start = message.find("ORA-") + 4
                    end = message.find(":", start)
                    if end == -1:
                        end = message.find(" ", start)
                    if end == -1:
                        end = len(message)
                        
                    error_code = "ORA-" + message[start:end].strip()
                    
                    if error_code not in error_summary:
                        error_summary[error_code] = {
                            "count": 0,
                            "last_occurrence": alert.get("timestamp"),
                            "sample_message": message[:200] + ('...' if len(message) > 200 else '')
                        }
                    error_summary[error_code]["count"] += 1
                    error_summary[error_code]["last_occurrence"] = alert.get("timestamp")
            
            return {
                "errors": alerts,
                "error_summary": error_summary,
                "total_errors": len(alerts)
            }
        
        except Exception as _:
            # Fallback to alternative views if available
            try:
                query = f"""
                SELECT * FROM (
                    SELECT timestamp, message_text
                    FROM v$diag_alert_ext
                    WHERE timestamp > SYSTIMESTAMP - INTERVAL '{hours}' HOUR
                        AND message_text LIKE '%ORA-%'
                        {error_filter}
                    ORDER BY timestamp DESC
                ) FETCH FIRST {row_limit} ROWS ONLY
                """
                with conn.cursor() as cursor:
                    cursor.execute(query)
                    alerts = [
                        {
                        "timestamp": row[0],
                        "message": row[1]
                    }
                    for row in cursor.fetchall()
                    ]
                
                # Simple count of errors if we can't group them
                error_count = len(alerts)
                
                return {
                    "errors": alerts,
                    "total_errors": error_count,
                    "note": "Limited access to alert log. Using v$diag_alert_ext view."
                }
            except Exception as e2:
                return {
                    "error": f"Could not access alert log: {str(e2)}",
                    "suggestion": "Check database permissions or try using OS-level access to alertlog.log"
                }

# End of file