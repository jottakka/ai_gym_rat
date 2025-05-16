from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from typing import List, Tuple, Union

from ai_gym_rat.core.llm_setup import get_llm
from ai_gym_rat.tools.wger_tools import WgerExerciseQueryTool
from ai_gym_rat.core.prompts import WORKOUT_AGENT_SYSTEM_PROMPT


def create_workout_agent_executor():
    """
    Creates and returns the LangChain agent executor for workout planning.
    LLM configuration is sourced from global AppSettings.
    """
    llm = get_llm()
    tools = [WgerExerciseQueryTool()]

    prompt = ChatPromptTemplate.from_messages([
        ("system", WORKOUT_AGENT_SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="chat_history", optional=True),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad")
    ])

    agent = create_openai_functions_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors="Check your Pydantic model for WgerExerciseQueryInput and ensure the LLM is calling the tool correctly with expected arguments.",
        max_iterations=10
    )
    return agent_executor

async def get_workout_plan_from_agent_async(
    agent_executor: AgentExecutor,
    user_query: str,
    chat_history: List[Union[HumanMessage, AIMessage]]
) -> Tuple[str, List[Union[HumanMessage, AIMessage]]]:
    """
    Invokes the agent executor asynchronously to get a workout plan.
    Manages and returns the updated chat history for conversational context.
    """
    try:
        response = await agent_executor.ainvoke({
            "input": user_query,
            "chat_history": chat_history
        })
        output_message = response.get("output", "Sorry, I couldn't generate a plan based on that.")

        updated_history = list(chat_history)
        updated_history.append(HumanMessage(content=user_query))
        updated_history.append(AIMessage(content=output_message))

        return output_message, updated_history
    except Exception as e:
        print(f"Error during agent execution: {e}")
        error_response = f"Sorry, an error occurred: {e}"
        updated_history_on_error = list(chat_history)
        updated_history_on_error.append(HumanMessage(content=user_query))
        updated_history_on_error.append(AIMessage(content=error_response))
        return error_response, updated_history_on_error