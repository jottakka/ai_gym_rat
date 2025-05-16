import asyncio
from typing import List, Union

from ai_gym_rat.services.workout_service import WorkoutPlannerService
from ai_gym_rat.core.config import settings
from langchain_core.messages import HumanMessage, AIMessage


async def run_cli_async():
    """
    Runs an asynchronous command-line interface for the AI Workout Architect
    using the WorkoutPlannerService.
    """
    print("Welcome to AI Workout Architect!")
    print(f"Using LLM Provider: {settings.LLM_PROVIDER}, Model: {settings.LLM_MODEL_NAME or 'default'}")
    print("Type 'quit' or 'exit' to stop.")

    try:
        planner_service = WorkoutPlannerService()
    except Exception as e:
        print(f"Failed to initialize WorkoutPlannerService: {e}")
        print("Please ensure your .env file is correctly configured and all dependencies are installed.")
        return

    chat_history: List[Union[HumanMessage, AIMessage]] = []

    while True:
        user_query = input("\nHow can I help you plan your workout today? \n> ")
        if user_query.lower() in ["quit", "exit"]:
            print("Stay fit! Goodbye!")
            break
        if not user_query.strip():
            continue

        print("\nThinking (async)...\n")
        
        try:
            agent_output, updated_chat_history = await planner_service.get_plan(
                user_query,
                chat_history
            )
            chat_history = updated_chat_history
        except Exception as e:
            # This handles errors from the service layer get_plan call itself
            print(f"An error occurred in the planner service: {e}")
            # Optionally, add an error message to chat_history if desired
            agent_output = "I'm sorry, but I encountered an internal error and can't assist right now."
            chat_history.append(HumanMessage(content=user_query))
            chat_history.append(AIMessage(content=agent_output))


        print("--- AI Workout Architect ---") # Changed title for brevity
        print(agent_output)
        print("----------------------------")

def main():
    asyncio.run(run_cli_async())

if __name__ == "__main__":
    main()