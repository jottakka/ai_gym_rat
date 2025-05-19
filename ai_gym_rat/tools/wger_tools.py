import httpx # Still needed for WgerAPIClient, but not directly used in the tool
from typing import List, Optional, Dict, Any, Type

from pydantic import ValidationError, BaseModel, Field, PrivateAttr
# model_validator is removed as we are using __init__

from langchain_core.tools import BaseTool

# Assuming WgerAPIClient is in a module, e.g., ai_gym_rat.clients.wger_client
# Adjust the import path as necessary for your project structure.
from ai_gym_rat.clients.wger_client import WgerAPIClient 

from ai_gym_rat.tools.wger_models import WgerExerciseInfoResponse 
# settings will be used by WgerAPIClient internally
from ai_gym_rat.core.config import settings


class WgerExerciseQueryInput(BaseModel):
    muscle_ids: Optional[List[int]] = Field(default=None, description="List of wger muscle numerical IDs. Example: [10, 8] for Quads and Hamstrings.")
    equipment_ids: Optional[List[int]] = Field(default=None, description="List of wger equipment numerical IDs. Example: [7] for Bodyweight, [3] for Dumbbell.")
    category_id: Optional[int] = Field(default=None, description="A single wger exercise category numerical ID. Example: 9 for Legs.")
    language_id: int = Field(default=settings.WGER_LANGUAGE_ID, description="Language ID for the results.") # Use settings for default
    limit: int = Field(default=10, description="Maximum number of exercises to fetch (default is 10).") 
    offset: int = Field(default=0, description="Offset for pagination (default is 0).")


class WgerExerciseQueryTool(BaseTool):
    name: str = "WgerExerciseQueryTool"
    description: str = (
        "Searches for exercises on the wger API based on muscle IDs, equipment IDs, or category ID. "
        "Use this to get a list of exercises matching specific criteria. "
        "You MUST provide numerical IDs for muscles, equipment, or category if filtering by them. "
        "Returns a list of exercises with their names, IDs, descriptions, main muscles, and equipment."
    )
    args_schema: Type[BaseModel] = WgerExerciseQueryInput
    
    # Use PrivateAttr for internal state that is not part of the tool's "schema"
    _api_client: WgerAPIClient = PrivateAttr()
 
    def __init__(self, api_client: WgerAPIClient):
        """
        Initializes the WgerExerciseQueryTool.
        The **data argument allows Pydantic/Langchain to pass field values.
        """
        super().__init__() # Initialize the BaseTool part
        self._api_client = api_client # Initialize the WgerAPIClient

    # The @model_validator and _initialize_api_client method have been removed.

    def _run(
        self,
        # Parameters are now handled by Pydantic model and passed to _arun
        **kwargs: Any 
    ) -> str:
        # This tool is async, _run should ideally not be called directly by Langchain if async is supported.
        raise NotImplementedError("WgerExerciseQueryTool is asynchronous; use _arun.")

    async def _arun(
        self,
        muscle_ids: Optional[List[int]] = None,
        equipment_ids: Optional[List[int]] = None,
        category_id: Optional[int] = None,
        language_id: Optional[int] = None, # This parameter from input schema, defaults in WgerExerciseQueryInput
        limit: int = 10, 
        offset: int = 0
    ) -> str:
        
        # Debugging information to understand what the tool is using
        print(f"[WgerExerciseQueryTool ASYNC] Input language_id for this call: {language_id}") 
        print(f"[WgerExerciseQueryTool ASYNC] Client's configured base URL: {self._api_client.base_url}")
        print(f"[WgerExerciseQueryTool ASYNC] Client's configured language ID (from its init): {self._api_client.language_id}")


        try:
            # Call the WgerAPIClient's method. It will use its own internal configuration
            # for base_url, api_key, and language_id set during its initialization.
            parsed_response = await self._api_client.get_exercises_info(
                muscle_ids=muscle_ids,
                equipment_ids=equipment_ids,
                category_id=category_id,
                limit=limit,
                offset=offset
            )

            if not parsed_response.results:
                return "No exercises found matching your criteria."

            formatted_exercises = []
            for i, ex_info in enumerate(parsed_response.results):
                details = f"Exercise {i+1} (ID: {ex_info.id}):\n"
                details += f"  Name: {ex_info.name or 'N/A'}\n"
                if ex_info.description:
                    desc_preview = (ex_info.description[:200] + '...') if len(ex_info.description) > 200 else ex_info.description
                    details += f"  Description: {desc_preview}\n"
                if ex_info.category_name:
                    details += f"  Category: {ex_info.category_name}\n"
                if ex_info.primary_muscles:
                    details += f"  Primary Muscles: {', '.join(ex_info.primary_muscles)}\n"
                if ex_info.secondary_muscles:
                    details += f"  Secondary Muscles: {', '.join(ex_info.secondary_muscles)}\n"
                if ex_info.equipment_required:
                    details += f"  Equipment: {', '.join(ex_info.equipment_required)}\n"
                else:
                    details += f"  Equipment: Bodyweight or Unspecified\n"
                
                formatted_exercises.append(details.strip())
            
            return "\n\n---\n\n".join(formatted_exercises)

        # Error handling is simplified as WgerAPIClient should handle its own detailed logging/printing of errors.
        except httpx.HTTPStatusError as e:
            return f"Error: Failed to fetch data from wger API. Status: {e.response.status_code}."
        except ValidationError:
            return "Error: API response structure from wger is not as expected."
        except Exception as e:
            print(f"[WgerExerciseQueryTool ASYNC] Forwarding unexpected error from client: {type(e).__name__} - {e}")
            return f"Error: An unexpected error occurred: {str(e)}"

