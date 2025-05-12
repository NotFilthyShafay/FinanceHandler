from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import chat, home
from app.utils.error_handler import add_exception_handlers

app = FastAPI(title="FastAPI LangChain Accountant")

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for security
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(home.router)
app.include_router(chat.router)

# Add global error handlers
add_exception_handlers(app)

# Run the FastAPI app
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000)
