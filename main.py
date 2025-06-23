from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging
import ollama # Make sure 'ollama' is imported
import json # You'll need this for JSON parsing

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Initialize Ollama client
# IMPORTANT: This will connect to Ollama running locally by default (http://localhost:11434).
# When deployed to Azure, you would need to run Ollama in another container
# and set this host to its internal URL (e.g., 'http://ollama-service-name:11434')
ollama_client = ollama.Client() # This line was missing or misplaced

# --- CORS Configuration ---
origins = [
    "http://localhost:4200",  # Allow your local Angular dev server
    "https://kind-rock-082362f1e.6.azurestaticapps.net" # Your deployed Angular app
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Data Model for Incoming Request ---
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

    # --- AI Integration Logic ---
    # 1. Craft a detailed prompt for the AI model
    prompt_parts = []
    prompt_parts.append("You are an AI fitness coach specializing in creating personalized workout plans.")
    prompt_parts.append("Generate a workout plan based on the following user preferences:")
    if data.age:
        prompt_parts.append(f"- Age: {data.age}")
    if data.time:
        prompt_parts.append(f"- Time available: {data.time} minutes")

    equipment_list = [eq_name for eq_name, has_eq in data.equipment.items() if has_eq]
    if equipment_list:
        prompt_parts.append(f"- Equipment available: {', '.join(equipment_list)}")
    else:
        prompt_parts.append("- Equipment available: None (bodyweight only)")

    if data.goal:
        prompt_parts.append(f"- Primary Goal: {data.goal}")
    if data.workoutType:
        prompt_parts.append(f"- Preferred Workout Type: {data.workoutType}")
    if data.adhdMode:
        prompt_parts.append("- Special consideration: User prefers ADHD-friendly mode (reduced movements, clear structure).")

    prompt_parts.append("\nYour response MUST be in JSON format, strictly adhering to this structure:")
    prompt_parts.append("""
{
    "status": "success",
    "workout": {
        "title": "A concise title for the workout",
        "description": "A brief description of the workout plan.",
        "warmup": [
            {"exercise": "Exercise Name (string)", "reps_or_time": "e.g., '10 reps' or '30 seconds' (string)"}
            // Ensure all values are correctly typed and quoted.
        ],
        "wod": [ // Workout of the Day (main workout)
            {
                "exercise": "Exercise Name (string)",
                "sets": 3, // (integer)
                "reps": 10, // (integer)
                "reps_or_time": "e.g., '10-12 reps' or '45 seconds' or '30-second hold' (string)"
                // IMPORTANT: For holds (like planks), use "reps_or_time" and put the duration as a string, e.g., "30-second hold".
                // Do NOT create new keys like "holds".
            }
        ],
        "cooldown": [
            {"exercise": "Exercise Name (string)", "reps_or_time": "e.g., '30 seconds hold' (string)"}
        ],
        "notes": "Any special instructions or advice (string)."
    }
}
""")
    # Add an even stronger emphasis on quoting and not adding extra keys
    prompt_parts.append("CRITICAL: Every string value in the JSON MUST be enclosed in double quotes. Do NOT add any keys not specified in the schema (e.g., do not use 'holds'). Provide only the JSON and nothing else.")

    full_prompt = "\n".join(prompt_parts)
    logger.info(f"Sending prompt to AI: {full_prompt}")

    try:
        # Send the request to the Ollama server
        # We're using 'llama2' as an example model. You can change this later.
        # Make sure you have downloaded the model using `ollama pull llama2`
        response_ai = ollama_client.generate(model='llama2', prompt=full_prompt, stream=False)

        # The actual content is usually in response_ai['response']
        ai_text_response = response_ai['response']
        logger.info(f"Raw AI response: {ai_text_response}")

        # Attempt to parse the JSON from the AI's response
        # The AI might include markdown code block, so we extract JSON
        if ai_text_response.startswith("```json"):
            json_string = ai_text_response.strip("```json").strip("```").strip()
        else:
            json_string = ai_text_response.strip()

        workout_data = json.loads(json_string)

        # Ensure the response adheres to your expected structure
        if "status" not in workout_data or "workout" not in workout_data:
             raise ValueError("AI response missing expected 'status' or 'workout' keys.")

        return workout_data

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse AI response as JSON: {e}")
        logger.error(f"Problematic AI response part: {ai_text_response[:500]}...")
        raise HTTPException(status_code=500, detail="Failed to parse AI workout plan. Please try again.")
    except ValueError as e:
        logger.error(f"AI response structure invalid: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Error calling Ollama API or processing response: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate workout plan. Please try again later.")
    # --- End AI Integration Logic ---

# Optional: A simple root endpoint to check if the API is running
@app.get("/")
async def read_root():
    return {"message": "Fitness Backend API is running!"}