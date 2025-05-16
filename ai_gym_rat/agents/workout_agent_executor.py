
from typing import List, Optional, Union, Tuple
import json # To parse the string output from UserInputParserTool

from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langchain_core.runnables import RunnablePassthrough
from langchain_core.agents import AgentFinish, AgentAction

from ai_gym_rat.clients.wger_client import WgerAPIClient
from ai_gym_rat.core.llm_setup import get_llm
from ai_gym_rat.tools.wger_tools import WgerExerciseQueryTool
from ai_gym_rat.tools.input_parser_tool import UserInputParserTool, ParsedUserInput
from ai_gym_rat.core.prompts import WORKOUT_AGENT_SYSTEM_PROMPT
                            

def create_workout_agent_executor():
    llm = get_llm()
    wger_client = WgerAPIClient() # Create client instance
    input_parser = UserInputParserTool(llm=llm) 
    wger_search = WgerExerciseQueryTool(api_client=wger_client) # Pass client to tool

    tools = [input_parser, wger_search]
    tools = [input_parser, wger_search]

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
        handle_parsing_errors="An error occurred while trying to process the tool's output. Please check the tool's implementation and the data it returned.",
        max_iterations=10,
    )
    return agent_executor


async def get_workout_plan_from_agent_async(
    agent_executor: AgentExecutor,
    user_query: str,
    chat_history: List[Union[HumanMessage, AIMessage]]
) -> Tuple[str, List[Union[HumanMessage, AIMessage]]]:
    
    updated_history = list(chat_history)

    try:
        response = await agent_executor.ainvoke({
            "input": user_query,
            "chat_history": updated_history # Pass the current history
        })
        output_message = response.get("output", "Sorry, I couldn't generate a plan based on that.")

        updated_history.append(HumanMessage(content=user_query))
        updated_history.append(AIMessage(content=output_message))

        return output_message, updated_history
    except Exception as e:
        print(f"Error during agent execution: {e}")
        error_response = f"Sorry, an error occurred while processing your request: {str(e)[:200]}"
        
        updated_history.append(HumanMessage(content=user_query))
        updated_history.append(AIMessage(content=error_response))
        return error_response, updated_history