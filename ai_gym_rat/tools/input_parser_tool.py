from typing import Type, Optional, List, Dict, Any
from pydantic import Field, BaseModel

from langchain_core.tools import BaseTool
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers.json import JsonOutputParser

from ai_gym_rat.core.llm_setup import get_llm
from ai_gym_rat.core.prompts import USER_INPUT_PARSER_SYSTEM_PROMPT

class ParsedUserInput(BaseModel):
    focus_areas: Optional[List[str]] = Field(default=None, description="List of main muscle groups or workout focus (e.g., ['legs', 'cardio']).")
    time_available_minutes: Optional[int] = Field(default=None, description="Workout duration in minutes.")
    tiredness_level: Optional[str] = Field(default=None, description="User's stated tiredness level (e.g., 'tired', 'normal', 'energetic').")
    location: Optional[str] = Field(default=None, description="Workout location (e.g., 'gym', 'home').")
    equipment_mentioned: Optional[List[str]] = Field(default=None, description="Specific equipment mentioned by the user (e.g., ['dumbbells']).")
    clarification_needed: bool = Field(default=False, description="True if essential information is missing.")
    clarification_question: Optional[str] = Field(default=None, description="A question to ask the user if clarification_needed is true.")
    
    # This field will hold the original query if no clarification is needed,
    # or a summary if some info was extracted but more is needed.
    processed_query_for_next_step: Optional[str] = Field(default=None, description="The query to use for the next step if no clarification is needed, or a summary.")


class UserInputParserToolInput(BaseModel):
    user_query: str = Field(description="The raw natural language query from the user.")


class UserInputParserTool(BaseTool):
    name: str = "UserInputParserTool"
    description: str = (
        "Parses the user's initial workout request to extract key constraints like "
        "focus areas, time, tiredness, location, and equipment. "
        "If essential information is missing, it formulates a clarification question. "
        "Returns structured data or a clarification question."
    )
    args_schema: Type[BaseModel] = UserInputParserToolInput
    llm: BaseChatModel

    def __init__(self, llm: BaseChatModel, **kwargs: Any):
        super().__init__(llm=llm, **kwargs)

    def _parse_llm_output_to_model(self, llm_json_output: Dict[str, Any]) -> ParsedUserInput:
        """Safely creates ParsedUserInput from LLM's JSON output."""
        return ParsedUserInput(
            focus_areas=llm_json_output.get("focus_areas"),
            time_available_minutes=llm_json_output.get("time_available_minutes"),
            tiredness_level=llm_json_output.get("tiredness_level"),
            location=llm_json_output.get("location"),
            equipment_mentioned=llm_json_output.get("equipment_mentioned"),
            clarification_needed=llm_json_output.get("clarification_needed", False),
            clarification_question=llm_json_output.get("clarification_question"),
            processed_query_for_next_step=llm_json_output.get("processed_query_for_next_step")
        )

    def _run(self, user_query: str) -> str:
        raise NotImplementedError("Subclasses must implement this method.")


    async def _arun(self, user_query: str) -> str:
        """
        Uses an LLM to parse the user query and extract constraints or ask for clarification.
        Returns a JSON string of the ParsedUserInput model.
        """
        prompt = ChatPromptTemplate.from_messages([
            ("system", USER_INPUT_PARSER_SYSTEM_PROMPT),
            # Provide format instructions to the LLM
            ("human", "User query: {user_query}\n\n{format_instructions}")
        ])
        
        # JsonOutputParser will guide the LLM to produce JSON and parse it into our Pydantic model
        parser = JsonOutputParser(pydantic_object=ParsedUserInput)
        
        chain = prompt | self.llm | parser

        try:
            llm_json_output = await chain.ainvoke({
                "user_query": user_query,
                "format_instructions": parser.get_format_instructions()
            })
            parsed_output = self._parse_llm_output_to_model(llm_json_output)

        except Exception as e:
            print(f"[UserInputParserTool ASYNC ERROR] Failed to parse LLM response: {e}")
            parsed_output = ParsedUserInput(
                clarification_needed=True,
                clarification_question="I had a little trouble understanding your request. Could you please rephrase or provide more details about your workout goals (focus, time, location, tiredness)?",
                processed_query_for_next_step=user_query
            )
        
        return parsed_output.model_dump_json()

