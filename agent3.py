import requests
import json
import time
import os
from dotenv import load_dotenv

# the third Agent (LLM) that checks for nearby centers, NGOs for donation
# Gets into work if the user sends a whatsapp message Donate.
# Sends the information back to user via whatsapp

load_dotenv()

API_KEY = os.getenv("API_KEY")
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent"
# Have used my home location.
location = "Dhakuria area of Kolkata in India"

def find_donation_centers(item_to_donate: str, location=location) -> str:
    """
    Uses the Gemini API with Google Search grounding to find local food donation centers.
    """
    print(f"Agent 3: Initiating search for donation centers accepting '{item_to_donate}' in '{location}'.")

    # The prompt directs the LLM to use the search tool and structure the output.
    user_query = (
        f"Find 3 local non-profit food banks or pantries within 5 kilometers of {location} "
        f"that specifically accept donations of '{item_to_donate}'. "
        f"Or accepts food as donation."
        f"For each one, provide the Name, full Street Address, and Phone Number. "
        f"Respond ONLY with a numbered list in this format: 1. Name, Address, Phone."
    )

    system_prompt = (
        "You are a local donation assistance service. Use the provided Google Search tool "
        "to find current, actionable contact information. Do not add any introductory or "
        "concluding text, only the structured list of contacts."
    )

    payload = {
        "contents": [{"parts": [{"text": user_query}]}],
        # Enable Google Search grounding (the essential web search capability)
        "tools": [{"google_search": {}}],
        "systemInstruction": {"parts": [{"text": system_prompt}]},
    }

    # Implement basic exponential backoff for robustness
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.post(
                f"{GEMINI_API_URL}?key={API_KEY}",
                headers={"Content-Type": "application/json"},
                data=json.dumps(payload),
                timeout=45 # Set a timeout for the API call
            )
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
            
            result = response.json()
            
            # Extract generated text
            generated_text = result.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
            
            if generated_text:
                return generated_text.strip()
            else:
                return "Agent 3: I could not find any suitable donation centers right now. Please try again later."

        except requests.exceptions.RequestException as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt) # Exponential backoff: 1s, 2s, 4s...
            else:
                return "Agent 3: Connection or API error. Could not complete the search."
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            return "Agent 3: An internal processing error occurred."

# driver code
if __name__ == '__main__':
    
#      
    result = find_donation_centers("5 lbs of ripened bananas", "Dhakuria area of Kolkata in India")
    print("\n--- AGENT 3 RESULT ---")
    print(result)
