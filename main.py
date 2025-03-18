from src.configs.utilites import execute_sql_files
from src.configs.settings import settings 
import uvicorn
from app import app

def run_app():
    try:
        execute_sql_files()  # Ensure SQL files are executed first
    except Exception as e:
        exit(1)  # Exit the app if there's an error

    uvicorn.run(
        "app:app",
        host="127.0.0.1",
        port=settings.PORT or 8000,  # Default to 8000 if port is not provided
        timeout_keep_alive=settings.SERVER_TIMEOUT,  
        reload=False,  # Set to True for development if needed
    )

if __name__ == "__main__":
    run_app()
