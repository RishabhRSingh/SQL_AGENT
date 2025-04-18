import os
import logging
from fastapi import HTTPException

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def validate_groq_api_key(api_key):
    """Validate that a GROQ API key is provided and has proper format"""
    if not api_key:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise HTTPException(
                status_code=400, 
                detail="No GROQ API key provided. Please either set the GROQ_API_KEY environment variable or provide it when initializing the agent."
            )
    
    if not api_key.startswith("gsk_"):
        logger.warning("The provided GROQ API key doesn't start with 'gsk_', which is the expected format")
    
    return api_key