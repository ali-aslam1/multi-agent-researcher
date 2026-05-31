import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from groq import Groq

# Load environment variables from .env file
load_dotenv()

app = FastAPI(
    title="Multi-Agent Research Assistant API",
    description="Backend service for autonomous research decomposes, synthesis, and aggregation.",
    version="1.0.0"
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify the exact domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ResearchRequest(BaseModel):
    query: str

class ResearchResponse(BaseModel):
    response: str
    status: str
    model_used: str

@app.get("/")
def read_root():
    return {
        "status": "online",
        "message": "Welcome to the Multi-Agent Research Assistant API. Check /docs for details."
    }

@app.post("/research", response_model=ResearchResponse)
def run_research(request: ResearchRequest):
    """
    Core research endpoint. In Phase 1, this establishes a single direct call
    to the Groq API to confirm end-to-end integration.
    """
    api_key = os.getenv("GROQ_API_KEY")
    
    # Check for empty, unset, or placeholder API keys
    if not api_key or "Replace this placeholder" in api_key or api_key == "YOUR_GROQ_API_KEY":
        # We fallback to a clear reminder response rather than a hard crash
        return ResearchResponse(
            response=(
                "API Key Not Configured!\n\n"
                "Please configure your Groq API Key in the `backend/.env` file:\n"
                "`GROQ_API_KEY=your_actual_groq_key`\n\n"
                "Once configured, restart the backend server and try your query again."
            ),
            status="API_KEY_MISSING",
            model_used="None"
        )

    try:
        # Initialize Groq Client
        client = Groq(api_key=api_key)
        
        # We use llama-3.3-70b-versatile as the modern default high-performance model on Groq
        model = "llama-3.3-70b-versatile"
        
        # Perform single direct call
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an elite research assistant. Provide structured, accurate, "
                        "and deeply informative responses to the user's research topic. "
                        "Structure your output using clear markdown headings, bullet points, and strong emphasis."
                    )
                },
                {
                    "role": "user",
                    "content": request.query
                }
            ],
            temperature=0.7,
            max_tokens=2048,
        )
        
        response_text = completion.choices[0].message.content
        
        return ResearchResponse(
            response=response_text,
            status="success",
            model_used=model
        )
        
    except Exception as e:
        # Gracefully handle API call failure
        error_msg = str(e)
        return ResearchResponse(
            response=f"Error communicating with Groq API:\n\n{error_msg}\n\nMake sure your API key in `backend/.env` is active and correct.",
            status="error",
            model_used="llama-3.3-70b-versatile"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
