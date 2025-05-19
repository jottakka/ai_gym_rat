from typing import Type, Any
from pydantic import BaseModel, Field

from langchain_core.tools import BaseTool
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate

from ai_gym_rat.tools.input_parser_tool import ParsedUserInput 
from ai_gym_rat.core.prompts import EXERCISE_REFINEMENT_SYSTEM_PROMPT

class ExerciseRefinementToolInput(BaseModel):
    parsed_user_constraints_json: str = Field(description="A JSON string representing the ParsedUserInput object containing all user constraints (focus, time, tiredness, location, equipment).")
    candidate_exercises_string: str = Field(description="A string listing candidate exercises, typically from WgerExerciseQueryTool.")

class ExerciseSelectionRefinementTool(BaseTool):
    name: str = "ExerciseSelectionRefinementTool"
    description: str = (
        "Refines a list of candidate exercises into a final, structured workout plan "
        "based on detailed user constraints. Assigns sets, reps, and suggests warm-up/cool-down. "
        "This tool should be used AFTER user input has been parsed and candidate exercises have been fetched."
    )
    args_schema: Type[BaseModel] = ExerciseRefinementToolInput
    llm: BaseChatModel

    def __init__(self, llm: BaseChatModel, **kwargs: Any):
        super().__init__(llm=llm, **kwargs)

    def _run(self, parsed_user_constraints_json: str, candidate_exercises_string: str) -> str:
        raise NotImplementedError("Subclasses must implement this method.")

    async def _arun(self, parsed_user_constraints_json: str, candidate_exercises_string: str) -> str:
        try:
            constraints = ParsedUserInput.model_validate_json(parsed_user_constraints_json)
        except Exception as e:
            print(f"[ExerciseRefinementTool ASYNC ERROR] Failed to parse constraints JSON: {e}")
            return "Error: Could not understand the provided user constraints for refinement."

        prompt = ChatPromptTemplate.from_template(EXERCISE_REFINEMENT_SYSTEM_PROMPT)
        
        chain = prompt | self.llm 

        try:
            response_message = await chain.ainvoke({
                "focus_areas": ", ".join(constraints.focus_areas) if constraints.focus_areas else "general",
                "time_available_minutes": constraints.time_available_minutes or "not specified",
                "tiredness_level": constraints.tiredness_level or "not specified",
                "location": constraints.location or "not specified",
                "equipment_mentioned": ", ".join(constraints.equipment_mentioned) if constraints.equipment_mentioned else "not specified",
                "candidate_exercises_string": candidate_exercises_string
            })
            return response_message.content
        except Exception as e:
            print(f"[ExerciseRefinementTool ASYNC ERROR] LLM call failed: {e}")
            return "Error: I encountered a problem while designing the final workout plan."
