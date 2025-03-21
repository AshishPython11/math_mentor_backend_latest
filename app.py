import os
from dotenv import load_dotenv
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from logging.config import dictConfig
from src.routers.auth import router as auth_router
from src.routers.chat_ai import router as chat_router
from src.routers.payment import router as payment_router
# from src.routers.ai_mcq import router as mcq_router
from src.configs.utilites import execute_sql_files
from src.routers.profile import router as profile_router

env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(env_file, override=True)

def configure_routes(app: FastAPI) -> None:
    """
    Register all routers on the application instance.
    """

    app.include_router(auth_router, prefix="/auth", tags=["Auth"])
    app.include_router(chat_router, prefix="/chatai", tags=["ChatAI"])
    app.include_router(payment_router, prefix="/payment", tags=["Payment"])
    # app.include_router(mcq_router, prefix="/mcq", tags=["mcq_routers"])
    app.include_router(profile_router, prefix="/profile", tags=["profile_router"])


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    """
    app = FastAPI()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

 
    configure_routes(app)

    return app
execute_sql_files() 



app = create_app()
