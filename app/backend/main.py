from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from typing import Optional
import os
import logging
from .database import DatabaseManager
from .agent import SQLAgent
from .utils import validate_groq_api_key

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="SQL Database Query API")

@app.get("/")
async def root():
    """Root endpoint that returns basic API information"""
    return {
        "status": "online",
        "message": "SQL Database Query API is running. Please use the Streamlit interface to interact with the application.",
        "endpoints": {
            "/upload-database/": "POST: Upload a SQLite database file",
            "/query/": "POST: Ask a question about the database",
            "/schema/": "GET: Get the schema information of the uploaded database"
        }
    }

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the database manager
db_manager = DatabaseManager()

# Global agent storage
sql_agent = None

@app.post("/upload-database/")
async def upload_database(
    db_file: UploadFile = File(...),
    api_key: Optional[str] = Form(None)
):
    """Upload a SQLite database file"""
    global sql_agent
    
    try:
        # Validate file extension
        if not db_file.filename.endswith('.db'):
            raise HTTPException(status_code=400, detail="Only SQLite (.db) files are supported")
        
        # Read the file content
        content = await db_file.read()
        
        # Save the database file
        result = db_manager.save_uploaded_db(content)
        
        if result["status"] != "success":
            raise HTTPException(status_code=500, detail=result["message"])
        
        # Validate API key
        api_key = validate_groq_api_key(api_key)
        
        # Initialize the agent
        try:
            sql_agent = SQLAgent(db_manager, api_key=api_key)
            logger.info("SQL Agent initialized successfully")
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        
        return {
            "status": "success", 
            "message": "Database uploaded and agent initialized", 
            "tables": result["tables"]
        }
    
    except Exception as e:
        logger.error(f"Error uploading database: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error uploading database: {str(e)}")

# from pydantic import BaseModel

# # Add this class
# class QuestionRequest(BaseModel):
#     question: str


# @app.post("/query/")
# async def query(question: str):
#     """Ask a question about the database in natural language"""
#     global sql_agent
    
#     if not sql_agent:
#         raise HTTPException(
#             status_code=400, 
#             detail="No database has been uploaded. Please upload a database first."
#         )
    
#     try:
#         # Run the agent
#         result = sql_agent.run(question)
        
#         return result
    
#     except Exception as e:
#         logger.error(f"Error querying database: {str(e)}")
#         raise HTTPException(status_code=500, detail=f"Error querying database: {str(e)}")



# @app.post("/query/")
# async def query(question: str):
#     """Ask a question about the database in natural language"""
#     global sql_agent
    
#     if not sql_agent:
#         raise HTTPException(
#             status_code=400, 
#             detail="No database has been uploaded. Please upload a database first."
#         )
    
#     try:
#         # Run the agent
#         result = sql_agent.run(question)
        
#         return result
    
#     except Exception as e:
#         logger.error(f"Error querying database: {str(e)}")
#         raise HTTPException(status_code=500, detail=f"Error querying database: {str(e)}")


from pydantic import BaseModel

class QuestionRequest(BaseModel):
    question: str

@app.post("/query/")
async def query(request: QuestionRequest):
    """Ask a question about the database in natural language"""
    global sql_agent
    
    if not sql_agent:
        raise HTTPException(
            status_code=400, 
            detail="No database has been uploaded. Please upload a database first."
        )
    
    try:
        # Run the agent
        result = sql_agent.run(request.question)
        
        return result
    
    except Exception as e:
        logger.error(f"Error querying database: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error querying database: {str(e)}")

@app.get("/schema/")
async def get_schema():
    """Get the schema information of the uploaded database"""
    if not db_manager.db_path:
        raise HTTPException(
            status_code=400, 
            detail="No database has been uploaded. Please upload a database first."
        )
    
    result = db_manager.get_schema_info()
    
    if result["status"] != "success":
        raise HTTPException(status_code=500, detail=result["message"])
    
    return result

@app.on_event("shutdown")
def shutdown_event():
    """Clean up on shutdown"""
    db_manager.cleanup()
    logger.info("Application shutting down, temporary files cleaned up")

if __name__ == "__main__":
    uvicorn.run("app.backend.main:app", host="0.0.0.0", port=8000, reload=True)