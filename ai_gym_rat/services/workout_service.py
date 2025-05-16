from typing import List, Tuple, Union
from langchain_core.messages import HumanMessage, AIMessage

from ai_gym_rat.agents.workout_agent_executor import (
    create_workout_agent_executor,
    get_workout_plan_from_agent_async
)
from ai_gym_rat.core.config import settings # To access settings if needed for agent creation

class WorkoutPlannerService:
    """
    Service layer to encapsulate the workout planning logic.
    """
    def __init__(self):
        """
        Initializes the service, including the LangChain agent executor.
        """
        try:
            self.agent_executor = create_workout_agent_executor()
        except ValueError as e:
            print(f"Error initializing LLM or Agent in WorkoutPlannerService: {e}")
            raise
        except Exception as e:
            print(f"An unexpected error occurred during WorkoutPlannerService setup: {e}")
            raise

    async def get_plan(
        self,
        user_query: str,
        chat_history: List[Union[HumanMessage, AIMessage]]
    ) -> Tuple[str, List[Union[HumanMessage, AIMessage]]]:
        """
        Gets a workout plan based on the user query and chat history.

        Args:
            user_query: The user's natural language request.
            chat_history: The current conversation history.

        Returns:
            A tuple containing the agent's response string and the updated chat history.
        """
        if not self.agent_executor:
            error_message = "WorkoutPlannerService not properly initialized."
            updated_history = list(chat_history)
            updated_history.append(HumanMessage(content=user_query))
            updated_history.append(AIMessage(content=error_message))
            return error_message, updated_history

        return await get_workout_plan_from_agent_async(
            self.agent_executor,
            user_query,
            chat_history
        )

