import os
import json
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from agent_graph import research_graph

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

@app.get("/")
def read_root():
    return {
        "status": "online",
        "message": "Welcome to the Multi-Agent Research Assistant API. Check /docs for details."
    }

@app.post("/research")
async def run_research(request: ResearchRequest):
    """
    Core research endpoint. Orchestrates a multi-agent system using LangGraph
    and streams stage/progress events back to the client using Server-Sent Events (SSE).
    """
    api_key = os.getenv("GROQ_API_KEY")
    
    # Check for empty, unset, or placeholder API keys
    if not api_key or "Replace this placeholder" in api_key or api_key == "YOUR_GROQ_API_KEY":
        async def key_missing_generator():
            yield "data: {}\n\n".format(json.dumps({
                "type": "status",
                "status": "API_KEY_MISSING",
                "message": (
                    "API Key Not Configured!\n\n"
                    "Please configure your Groq API Key in the `backend/.env` file:\n"
                    "`GROQ_API_KEY=your_actual_groq_key`\n\n"
                    "Once configured, restart the backend server and try your query again."
                )
            }))
        return StreamingResponse(key_missing_generator(), media_type="text/event-stream")

    async def event_generator():
        queue = asyncio.Queue()

        # Initialize the graph state
        initial_state = {
            "query": request.query,
            "sub_questions": [],
            "scraped_results": {},
            "summaries": {},
            "contradictions": "",
            "source_urls": [],
            "final_report": ""
        }

        # Run the graph in a background task
        async def run_graph():
            try:
                # Stream the LangGraph execution steps
                async for event in research_graph.astream(initial_state):
                    await queue.put({"type": "node", "event": event})
                await queue.put({"type": "done"})
            except Exception as e:
                import traceback
                traceback.print_exc()
                await queue.put({"type": "error", "message": str(e)})

        graph_task = asyncio.create_task(run_graph())

        try:
            while True:
                item = await queue.get()
                
                if item["type"] == "done":
                    break
                elif item["type"] == "error":
                    yield "data: {}\n\n".format(json.dumps({
                        "type": "status",
                        "status": "error",
                        "message": item["message"]
                    }))
                    break
                elif item["type"] == "node":
                    event = item["event"]
                    node_name = list(event.keys())[0]
                    node_output = event[node_name]
                    
                    payload = {"type": "status", "node": node_name}
                    
                    if node_name == "orchestrator":
                        payload["status"] = "decomposed"
                        payload["sub_questions"] = node_output.get("sub_questions", [])
                    elif node_name == "search":
                        payload["status"] = "searched"
                        payload["scraped_results"] = node_output.get("scraped_results", {})
                        payload["source_urls"] = node_output.get("source_urls", [])
                    elif node_name == "summarizer":
                        payload["status"] = "summarized"
                        payload["summaries"] = node_output.get("summaries", {})
                    elif node_name == "critic":
                        payload["status"] = "critiqued"
                        payload["contradictions"] = node_output.get("contradictions", "")
                    elif node_name == "aggregator":
                        payload["status"] = "completed"
                        payload["final_report"] = node_output.get("final_report", "")
                        payload["source_urls"] = initial_state.get("source_urls", []) # Fallback/Reference
                        
                    yield "data: {}\n\n".format(json.dumps(payload))
        except asyncio.CancelledError:
            graph_task.cancel()
            raise
        finally:
            if not graph_task.done():
                graph_task.cancel()

    return StreamingResponse(event_generator(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
