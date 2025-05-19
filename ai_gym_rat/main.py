import asyncio
from typing import List, Union, Optional, Callable, Awaitable

from fastapi import FastAPI, HTTPException, Body, Request, Response
from fastapi.routing import APIRoute
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn 
import io
from contextlib import redirect_stdout, asynccontextmanager
import json # For pretty printing JSON bodies

# Assuming your project structure and imports
from ai_gym_rat.services.workout_service import WorkoutPlannerService
from ai_gym_rat.core.config import settings
from langchain_core.messages import HumanMessage, AIMessage


# --- Pydantic Models for API ---
class Message(BaseModel):
    """Represents a single message in the chat history."""
    role: str 
    content: str

class PlanRequest(BaseModel):
    """Request model for the workout plan endpoint."""
    user_query: str
    chat_history: Optional[List[Message]] = []

class PlanResponse(BaseModel):
    """Response model for the workout plan endpoint."""
    agent_output: str
    updated_chat_history: List[Message]
    server_logs: Optional[List[str]] = None 

# --- Global variable for the service ---
planner_service: Optional[WorkoutPlannerService] = None

# --- Lifespan manager for startup and shutdown ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    global planner_service
    print("Attempting to initialize WorkoutPlannerService...")
    try:
        planner_service = WorkoutPlannerService()
        print(f"Successfully initialized WorkoutPlannerService. Using LLM Provider: {settings.LLM_PROVIDER}, Model: {settings.LLM_MODEL_NAME or 'default'}")
    except Exception as e:
        print(f"CRITICAL: Failed to initialize WorkoutPlannerService at startup: {e}")
        planner_service = None
    
    print("AI Workout Architect API started.")
    yield 
    print("AI Workout Architect API shutting down.")
    if planner_service:
        pass 

class LoggingAPIRoute(APIRoute):
    def get_route_handler(self) -> Callable:
        original_route_handler = super().get_route_handler()

        async def custom_route_handler(request: Request) -> Response:
            request.state.body_bytes = await request.body()
            return await original_route_handler(request)

        return custom_route_handler

app = FastAPI(
    title="AI Workout Architect API",
    description="API to get personalized workout plans.",
    version="1.0.0",
    lifespan=lifespan
)
app.router.route_class = LoggingAPIRoute


# --- HTTP Logging Middleware ---
@app.middleware("http")
async def http_logging_middleware(request: Request, call_next: Callable[[Request], Awaitable[Response]]):
    http_logs: List[str] = []
    request.state.http_logs = http_logs # Make logs accessible to the endpoint

    http_logs.append("--- HTTP Request ---")
    http_logs.append(f"Method: {request.method}")
    http_logs.append(f"URL: {request.url}")
    http_logs.append(f"Client: {request.client.host}:{request.client.port}")
    
    http_logs.append("Headers:")
    for name, value in request.headers.items():
        http_logs.append(f"  {name}: {value}")

    # Log request body
    # body_bytes = await request.body() # This consumes the body
    body_bytes = getattr(request.state, "body_bytes", b"") # Get from LoggingAPIRoute
    if body_bytes:
        try:
            body_json = json.loads(body_bytes.decode('utf-8'))
            http_logs.append("Body (JSON):")
            http_logs.append(json.dumps(body_json, indent=2))
        except json.JSONDecodeError:
            http_logs.append("Body (Text):")
            http_logs.append(body_bytes.decode('utf-8', errors='replace')) # errors='replace' for non-utf8
        except Exception as e:
            http_logs.append(f"Body (Error decoding): {e}")
    else:
        http_logs.append("Body: (empty)")
    
    http_logs.append("--- End HTTP Request ---")


    response = await call_next(request) # Process the request

    http_logs.append("--- HTTP Response ---")
    http_logs.append(f"Status Code: {response.status_code}")
    
    # Log response headers
    http_logs.append("Headers:")
    for name, value in response.headers.items():
        http_logs.append(f"  {name}: {value}")


    response_body_bytes = b""
    async for chunk in response.body_iterator: # type: ignore
        response_body_bytes += chunk
    
    if response_body_bytes:
        try:
            # Attempt to decode as JSON first
            body_json = json.loads(response_body_bytes.decode('utf-8'))
            http_logs.append("Body (JSON):")
            http_logs.append(json.dumps(body_json, indent=2))
        except json.JSONDecodeError:
            # Fallback to text if not JSON
            http_logs.append("Body (Text):")
            http_logs.append(response_body_bytes.decode('utf-8', errors='replace'))
        except Exception as e:
            http_logs.append(f"Body (Error decoding response): {e}")

    else:
        http_logs.append("Body: (empty or streaming not captured here)")
    http_logs.append("--- End HTTP Response ---")
    
    # The response object's body_iterator is now consumed.
    # We need to return a new response with the consumed body.
    return Response(
        content=response_body_bytes,
        status_code=response.status_code,
        headers=dict(response.headers),
        media_type=response.media_type
    )


origins = [
    "http://localhost", 
    "http://localhost:8000", 
    "null", 
    "http://127.0.0.1:5500",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True, 
    allow_methods=["*"],    
    allow_headers=["*"],    
)

# --- API Endpoints ---
@app.post("/plan", response_model=PlanResponse)
async def get_workout_plan(request: Request, payload: PlanRequest = Body(...)): # Inject Request object
    global planner_service
    if planner_service is None:
        raise HTTPException(
            status_code=503, 
            detail="WorkoutPlannerService is not available. Please check server logs."
        )

    langchain_chat_history: List[Union[HumanMessage, AIMessage]] = []
    for msg in payload.chat_history: # Use payload for request body
        if msg.role.lower() == "human":
            langchain_chat_history.append(HumanMessage(content=msg.content))
        elif msg.role.lower() == "ai":
            langchain_chat_history.append(AIMessage(content=msg.content))

    log_capture_stream = io.StringIO()
    console_logs: List[str] = []
    # Retrieve HTTP logs from middleware (if any)
    http_logs_from_middleware = getattr(request.state, "http_logs", [])
    all_server_logs = list(http_logs_from_middleware) # Start with HTTP logs

    with redirect_stdout(log_capture_stream):
        try:
            print(f"CONSOLE: Received query for /plan: '{payload.user_query}'")
            print(f"CONSOLE: Incoming chat history length: {len(langchain_chat_history)}")

            agent_output_content, updated_langchain_chat_history = await planner_service.get_plan(
                payload.user_query,
                langchain_chat_history
            )
            
            print(f"CONSOLE: Plan generated. Output length: {len(agent_output_content)}")
            
            response_chat_history: List[Message] = []
            for msg_item in updated_langchain_chat_history:
                if isinstance(msg_item, HumanMessage):
                    response_chat_history.append(Message(role="human", content=msg_item.content))
                elif isinstance(msg_item, AIMessage):
                    response_chat_history.append(Message(role="ai", content=msg_item.content))
            
            print(f"CONSOLE: Sending response. AI output snippet: {agent_output_content[:100]}...")
            
            log_content = log_capture_stream.getvalue()
            if log_content:
                console_logs = [line for line in log_content.strip().split('\n') if line.strip()]
            
            all_server_logs.extend(console_logs) # Add console logs

            return PlanResponse(
                agent_output=agent_output_content,
                updated_chat_history=response_chat_history,
                server_logs=all_server_logs
            )

        except Exception as e:
            print(f"CONSOLE ERROR in /plan endpoint: {str(e)}")
            log_content = log_capture_stream.getvalue()
            if log_content:
                console_logs.extend([line for line in log_content.strip().split('\n') if line.strip() and line not in console_logs])
            
            all_server_logs.extend(console_logs)
            # Ensure error logs are also included
            error_log_entry = f"EXCEPTION: {str(e)}"
            if error_log_entry not in all_server_logs:
                 all_server_logs.append(error_log_entry)
            raise HTTPException(
                status_code=500, 
                detail=f"An internal error occurred: {str(e)}"
            )
        finally:
            log_capture_stream.close()


@app.get("/health", summary="Health Check", description="Returns the operational status of the API.")
async def health_check():
    global planner_service
    if planner_service is None:
         return {"status": "unhealthy", "detail": "WorkoutPlannerService not initialized"}
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    print("Starting Uvicorn server for development...")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, log_level="info", reload=True)
