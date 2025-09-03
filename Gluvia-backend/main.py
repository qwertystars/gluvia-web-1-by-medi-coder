from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import auth_routes, consolidated_routes
from database import create_tables
from logging_config import setup_logging

# Initialize logging
setup_logging()

app = FastAPI(
    title="Gluvia - Insulin Management System",
    description="A comprehensive insulin dose tracking and management system",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Create database tables on startup
@app.on_event("startup")
def startup_event():
    create_tables()

# Include routers - using consolidated routes for prescriptions
app.include_router(auth_routes.router, prefix="/auth", tags=["authentication"])
app.include_router(consolidated_routes.router)

@app.get("/")
def home():
    return {"message": "Gluvia backend API is running with consolidated routes and safety validators!"}
