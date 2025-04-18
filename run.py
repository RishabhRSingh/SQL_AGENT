# run.py

import subprocess
import time
import os
import threading

def run_backend():
    # Setting up environment variables
    env = os.environ.copy()
    
    # Check if GROQ_API_KEY is in environment
    if "GROQ_API_KEY" not in env:
        print("Warning: GROQ_API_KEY environment variable is not set")
        print("You will need to provide a GROQ API key in the application")

    # Run the FastAPI backend
    subprocess.run(["uvicorn", "app.backend.main:app", "--host", "0.0.0.0", "--port", "8000"])

def run_frontend():
    # Wait for backend to start
    time.sleep(3)
    
    # Setting up environment variables
    env = os.environ.copy()
    env["API_URL"] = "http://localhost:8000"
    
    # Run Streamlit frontend
    subprocess.run(["streamlit", "run", "app/frontend/streamlit_app.py"], env=env)

if __name__ == "__main__":
    # Start backend in a separate thread
    backend_thread = threading.Thread(target=run_backend)
    backend_thread.start()
    
    # Start frontend
    run_frontend()