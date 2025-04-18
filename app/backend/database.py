from sqlalchemy import create_engine, inspect
import tempfile
import os
import sqlite3
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = None
        self.engine = None
    
    def save_uploaded_db(self, db_file):
        """Save the uploaded database file to a temporary location"""
        try:
            # Create a temporary file path
            self.db_path = os.path.join(self.temp_dir, "uploaded.db")
            
            # Write the file
            with open(self.db_path, "wb") as f:
                f.write(db_file)
            
            # Create SQLAlchemy engine
            self.engine = create_engine(f"sqlite:///{self.db_path}")
            
            # Test connection
            inspector = inspect(self.engine)
            tables = inspector.get_table_names()
            
            logger.info(f"Database uploaded successfully with tables: {tables}")
            return {"status": "success", "tables": tables}
        
        except Exception as e:
            logger.error(f"Error saving database: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    # def get_schema_info(self):
    #     """Get schema information from the database"""
    #     if not self.engine:
    #         return {"status": "error", "message": "No database connected"}
        
    #     try:
    #         inspector = inspect(self.engine)
    #         tables = inspector.get_table_names()
            
    #         schema_info = {}
    #         for table in tables:
    #             columns = inspector.get_columns(table)
    #             schema_info[table] = {
    #                 "columns": [{"name": col["name"], "type": str(col["type"])} for col in columns]
    #             }
                
    #             # Get a sample of data
    #             with self.engine.connect() as conn:
    #                 sample_data = conn.execute(f"SELECT * FROM {table} LIMIT 3").fetchall()
    #                 schema_info[table]["sample_data"] = [dict(row) for row in sample_data]
            
    #         return {"status": "success", "schema": schema_info}
        
    #     except Exception as e:
    #         logger.error(f"Error getting schema info: {str(e)}")
    #         return {"status": "error", "message": str(e)}

    def get_schema_info(self):
        """Get schema information from the database"""
        if not self.engine:
            return {"status": "error", "message": "No database connected"}
        
        try:
            inspector = inspect(self.engine)
            tables = inspector.get_table_names()
            
            schema_info = {}
            for table in tables:
                columns = inspector.get_columns(table)
                schema_info[table] = {
                    "columns": [{"name": col["name"], "type": str(col["type"])} for col in columns]
                }
                
                # Get a sample of data - let's use sqlite3 directly instead of SQLAlchemy
                conn = sqlite3.connect(self.db_path)
                conn.row_factory = sqlite3.Row
                try:
                    cursor = conn.cursor()
                    cursor.execute(f"SELECT * FROM {table} LIMIT 15")
                    sample_data = [dict(row) for row in cursor.fetchall()]
                    schema_info[table]["sample_data"] = sample_data
                    cursor.close()
                except Exception as e:
                    logger.error(f"Error getting sample data for {table}: {str(e)}")
                    schema_info[table]["sample_data"] = []
                finally:
                    conn.close()
            
            return {"status": "success", "schema": schema_info}
        
        except Exception as e:
            logger.error(f"Error getting schema info: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def execute_query(self, query):
        """Execute a SQL query on the database"""
        if not self.db_path:
            return {"status": "error", "message": "No database connected"}
        
        try:
            # Use sqlite3 directly for better control
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Execute the query
            cursor.execute(query)
            
            # Fetch results
            results = [dict(row) for row in cursor.fetchall()]
            
            # Close connections
            cursor.close()
            conn.close()
            
            return {"status": "success", "results": results}
        
        except Exception as e:
            logger.error(f"Error executing query: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def cleanup(self):
        """Clean up temporary files"""
        try:
            if self.db_path and os.path.exists(self.db_path):
                os.remove(self.db_path)
            os.rmdir(self.temp_dir)
            logger.info("Temporary files cleaned up")
        except Exception as e:
            logger.error(f"Error cleaning up: {str(e)}")