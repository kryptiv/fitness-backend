from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# --- CORS Configuration ---
# This is CRUCIAL for your Angular frontend to talk to this backend
# When your Angular app is running locally, it's typically on http://localhost:4200
# When deployed, it will have a different URL.
# Replace 'http://localhost:4200' with your actual frontend URL(s) when deployed.
origins = [
    # "http://localhost:4200",  # Allow your local Angular dev server
    # "https://your-deployed-angular-app.azurestaticapps.net", # Example for deployed Angular app
    # "https://your-frontend-container-app.azurecontainerapps.io" # If hosted directly in ACA
    "https://fitness-backend-api.ashyflower-5c5b2fa1.westus3.azurecontainerapps.io/"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,       # List of allowed origins
    allow_credentials=True,      # Allow cookies/authorization headers
    allow_methods=["*"],         # Allow all HTTP methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],         # Allow all headers
)

# --- Data Model for Incoming Request ---
# This defines the expected structure of the JSON data from your Angular frontend
class FormData(BaseModel):
    age: int | None = None
    time: int | None = None
    equipment: dict | None = None # This will be a dict like {"dumbbells": true, ...}
    goal: str | None = None
    workoutType: str | None = None
    adhdMode: bool = False

# --- API Endpoint ---
@app.post("/generate-workout")
async def generate_workout(data: FormData):
    logger.info(f"Received data from frontend: {data.model_dump_json()}")

    # TODO: Placeholder for AI integration
    # In the future, you will pass 'data' to your open-source AI model here
    # and get a generated workout back.
    # For now, let's return a mock workout.
    mock_workout = {
        "title": "Quick & Effective Full Body Blast",
        "description": "A customized workout designed for your goals and available time/equipment.",
        "warmup": [
            {"exercise": "Arm Circles", "reps_or_time": "10 forward, 10 backward"},
            {"exercise": "Leg Swings", "reps_or_time": "10 each leg"},
            {"exercise": "Dynamic Stretches", "reps_or_time": "5 minutes"}
        ],
        "wod": [
            {"exercise": "Air Squats", "sets": 3, "reps": 10},
            {"exercise": "Push-ups (or Knee Push-ups)", "sets": 3, "reps": 8},
            {"exercise": "Plank", "sets": 3, "reps_or_time": "30-60 seconds hold"},
            {"exercise": "Dumbbell Rows (if dumbbells available)", "sets": 3, "reps": 10}
        ],
        "cooldown": [
            {"exercise": "Static Stretches", "reps_or_time": "5 minutes"}
        ],
        "notes": f"Workout generated based on your settings: Age={data.age}, Time={data.time}, ADHD Mode={data.adhdMode}"
    }

    # You would typically have the AI generate this based on 'data'
    return {"status": "success", "workout": mock_workout}

# Optional: A simple root endpoint to check if the API is running
@app.get("/")
async def read_root():
    return {"message": "Fitness Backend API is running!"}