import json
import re # Import the regular expression module
from typing import List, Optional
from pydantic import BaseModel, ValidationError
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import ollama
import os

# ... (Your existing Pydantic models: Exercise, WorkoutDay, WorkoutPlan) ...

# Ollama client initialization
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://ollama-service.default.svc.cluster.local:8080")
ollama_client = ollama.Client(host=OLLAMA_HOST)

app = FastAPI()

# CORS configuration
origins = [
    "http://localhost:4200", # For local Angular development
    "https://kind-rock-082362f1e.6.azurestaticapps.net" # Your Azure Static Web App URL
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def parse_workout_plan(ai_response: str) -> WorkoutPlan:
    """
    Parses the AI's response to extract and validate the workout plan JSON.
    """
    # Step 1: Extract JSON string using regex, handling potential leading/trailing text and markdown
    # This regex looks for an optional prefix, then ```json followed by content, then ```, then optional suffix
    match = re.search(r'```json\s*(.*?)\s*```', ai_response, re.DOTALL)
    if match:
        json_str = match.group(1).strip()
        print(f"Extracted JSON string from markdown block.")
    else:
        # Fallback if no markdown block, try to find the first '{' and last '}'
        # This is less robust but can handle cases where markdown is missing
        start = ai_response.find('{')
        end = ai_response.rfind('}')
        if start != -1 and end != -1 and end > start:
            json_str = ai_response[start : end + 1].strip()
            print(f"Extracted JSON string by finding brackets.")
        else:
            # If no JSON-like structure is found at all
            print(f"No JSON markdown block or clear JSON structure found in AI response.")
            raise ValueError("No parsable JSON content found in AI response.")

    # Step 2: Parse the JSON string
    try:
        raw_data = json.loads(json_str)
        print(f"Parsed raw JSON data: {raw_data}")
    except json.JSONDecodeError as e:
        print(f"JSONDecodeError: {e} - Raw string: {json_str[:500]}...") # Log partial string
        raise ValueError(f"Failed to decode JSON: {e}")

    # Step 3: Handle the nested "workout" key if present
    # If the model wraps the workout plan in a "workout" key, extract it
    if isinstance(raw_data, dict) and "workout" in raw_data:
        final_data = raw_data["workout"]
        print(f"Extracted 'workout' key from JSON.")
    else:
        final_data = raw_data
        print(f"No 'workout' key found, using raw data as final_data.")


    # Step 4: Validate with Pydantic
    try:
        workout_plan = WorkoutPlan(**final_data)
        print(f"Successfully validated workout plan with Pydantic.")
        return workout_plan
    except ValidationError as e:
        print(f"Pydantic Validation Error: {e.errors()}")
        raise ValueError(f"Failed to validate workout plan with Pydantic: {e.errors()}")


@app.post("/generate-workout")
async def generate_workout(request: Request):
    try:
        data = await request.json()
        user_preference = data.get("userPreference")
        if not user_preference:
            raise HTTPException(status_code=400, detail="User preference is required.")

        full_prompt = f"""
        You are an AI assistant specialized in creating workout plans.
        Given the user's preferences, generate a detailed workout plan in JSON format.
        The JSON must adhere to the following structure:
        {{
            "title": "Workout Plan Title",
            "description": "A brief description of the workout plan.",
            "warmup": [
                {{"exercise": "Exercise Name", "reps_or_time": "Reps or Time (e.g., '10 reps' or '30 seconds')"}}
            ],
            "wod": [
                {{
                    "day": "Day of the week (e.g., Monday)",
                    "focus": "Focus of the day (e.g., Upper Body)",
                    "exercises": [
                        {{"exercise": "Exercise Name", "sets": "Number of sets", "reps": "Reps/Time/Distance"}},
                        // ... more exercises for the day
                    ]
                }}
            ],
            "cooldown": [
                {{"exercise": "Exercise Name", "reps_or_time": "Reps or Time (e.g., '30 seconds')"}}
            ]
        }}
        Ensure all fields are present and correctly formatted as per the structure.
        Make sure the entire output is valid JSON, surrounded by ```json and ```.
        User preferences: {user_preference}
        """

        # The model is phi3:mini
        response_ai = ollama_client.generate(model='phi3:mini', prompt=full_prompt, stream=False)

        # Log the raw AI response for debugging
        print(f"INFO:main:Raw AI response: {response_ai['response']}")

        workout_plan_obj = parse_workout_plan(response_ai['response'])
        print(f"INFO:main:Parsed workout plan: {workout_plan_obj.dict()}")
        return {"message": "Workout plan generated successfully!", "workout_plan": workout_plan_obj.dict()}

    except ValueError as e:
        # Catch parsing/validation errors from parse_workout_plan
        raise HTTPException(status_code=500, detail=f"Failed to parse AI workout plan: {e}")
    except Exception as e:
        # Catch any other unexpected errors
        print(f"ERROR:main:An unexpected error occurred: {e}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")