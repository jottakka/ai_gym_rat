import asyncio

import better_exceptions
from ai_gym_rat.agents.workout_agent_executor import (
    create_workout_agent_executor,
    get_workout_plan_from_agent_async
)
from ai_gym_rat.core.config import settings
from langchain_core.messages import HumanMessage, AIMessage
from typing import List, Union
from rich.traceback import install

async def run_cli_async():
    """
    Runs an asynchronous command-line interface for the AI Workout Architect.
    """
    print("Welcome to AI Workout Architect!")
    print(f"Using LLM Provider: {settings.LLM_PROVIDER}, Model: {settings.LLM_MODEL_NAME or 'default'}")
    print("Type 'quit' or 'exit' to stop.")

    try:
        agent_executor = create_workout_agent_executor()
    except ValueError as e:
        print(f"Error initializing LLM or Agent: {e}")
        print("Please ensure your .env file is correctly configured with API keys and settings.")
        return
    except Exception as e:
        print(f"An unexpected error occurred during setup: {e}")
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

        agent_output, updated_chat_history = await get_workout_plan_from_agent_async(
            agent_executor,
            user_query,
            chat_history
        )
        
        chat_history = updated_chat_history

        print("--- AI Workout Architect Plan ---")
        print(agent_output)
        print("---------------------------------")

install(show_locals=True)
def main():
    better_exceptions.hook()
    asyncio.run(run_cli_async())

if __name__ == "__main__":
    main()