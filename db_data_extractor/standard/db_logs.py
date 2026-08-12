# Relative Path: db_data_extractor\standard\db_logs.py
"""
Oracle Database Logs Module

This module provides specialized tools for accessing and analyzing Oracle database logs,
including alert logs, trace files, and audit logs.
"""

import logging
from .connection import OracleConnection

# Get logger for this module
logger = logging.getLogger('db_data_extractor.standard.db_logs')
logger.info('Database Logs module loaded')


class DatabaseLogExplorer:
    """
    Tools for exploring and analyzing Oracle database logs, including
    alert logs, trace files, and audit logs.
    """
    
    def __init__(self, connection=None):
        """
        Initialize with an existing connection or create a new one.
        
        Args:
            connection (OracleConnection, optional): Existing connection to use
        """
        self.connection = connection or OracleConnection()
        logger.debug('DatabaseLogExplorer initialized')
    
    def get_database_alerts(self, hours=24, severity=None, limit=100):
        """
        Get recent database alert log entries from X$DBGALERTEXT or DBA_ALERT_HISTORY
        if available (requires appropriate privileges).
        
        Args:
            hours (int): Number of hours to look back
            severity (str, optional): Filter by severity level ('WARNING', 'ERROR', 'CRITICAL', etc)
            limit (int, optional): Maximum number of alert entries to return. Default is 100.
            
        Returns:
            list: List of dictionaries with alert details
        """
        conn = self.connection.connect()
        
        try:
            # Try to access alert log data
            # First attempt X$DBGALERTEXT (requires SYSDBA)
            try:
                severity_filter = f"AND upper(message_text) LIKE '%{severity.upper()}%'" if severity else ""
                
                # Base query
                query = f"""
                SELECT * FROM (
                    SELECT originating_timestamp, component_id, host_id, host_address,
                           message_text, message_type
                    FROM X$DBGALERTEXT
                    WHERE originating_timestamp > SYSTIMESTAMP - INTERVAL '{hours}' HOUR
                    {severity_filter}
                    ORDER BY originating_timestamp DESC
                ) FETCH FIRST {limit} ROWS ONLY
                """
                
                cursor = conn.cursor()
                cursor.execute(query)
                
                alerts = [
                    {
                        "timestamp": row[0],
                        "component": row[1],
                        "host": row[2],
                        "host_address": row[3],
                        "message": row[4],
                        "type": row[5]
                    }
                    for row in cursor.fetchall()
                ]
                cursor.close()
                return alerts
            except Exception:
                # Fall back to DBA_ALERT_HISTORY
                severity_filter = f"AND upper(reason) LIKE '%{severity.upper()}%'" if severity else ""
                
                # Base query
                query = f"""
                SELECT * FROM (
                    SELECT sequence_id, reason, time_suggested, repair_script,
                        message, advisor_name
                    FROM DBA_ALERT_HISTORY
                    WHERE time_suggested > SYSTIMESTAMP - INTERVAL '{hours}' HOUR
                    {severity_filter}
                    ORDER BY time_suggested DESC
                ) FETCH FIRST {limit} ROWS ONLY
                """
                
                cursor = conn.cursor()
                cursor.execute(query)
                
                alerts = [
                    {
                        "sequence_id": row[0],
                        "reason": row[1],
                        "timestamp": row[2],
                        "repair_script": row[3],
                        "message": row[4],
                        "advisor": row[5]
                    }
                    for row in cursor.fetchall()
                ]
                cursor.close()
                return alerts
        except Exception as e:
            return {"error": f"Could not retrieve database alerts: {str(e)}"}
        finally:
            conn.close()

# End of the file