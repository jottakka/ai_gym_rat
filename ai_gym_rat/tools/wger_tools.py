import httpx
from typing import List, Optional, Dict, Any, Type
from pydantic import ValidationError, BaseModel, Field

from langchain_core.tools import BaseTool

from ai_gym_rat.core.config import settings
from ai_gym_rat.tools.wger_models import WgerExerciseInfoResponse 

class WgerExerciseQueryInput(BaseModel):
    muscle_ids: Optional[List[int]] = Field(default=None, description="List of wger muscle numerical IDs. Example: [10, 8] for Quads and Hamstrings.")
    equipment_ids: Optional[List[int]] = Field(default=None, description="List of wger equipment numerical IDs. Example: [7] for Bodyweight, [3] for Dumbbell.")
    category_id: Optional[int] = Field(default=None, description="A single wger exercise category numerical ID. Example: 9 for Legs.")
    language_id: int = Field(default=2, description="Language ID for the results (default is 2 for English).")
    limit: int = Field(default=5, description="Maximum number of exercises to fetch (default is 5).")
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

    def _build_params(
        self,
        language_id: int,
        muscle_ids: Optional[List[int]],
        equipment_ids: Optional[List[int]],
        category_id: Optional[int],
        limit: int,
        offset: int
    ) -> Dict[str, Any]:
        """
        Builds the dictionary of parameters for the API request.
        List parameters (muscle_ids, equipment_ids) are kept as lists
        for httpx to handle as repeated query parameters.
        """
        params: Dict[str, Any] = {
            "language": language_id,
            "limit": limit,
            "offset": offset,
            "status": 2 # Approved exercises
        }

        if category_id is not None:
            params["category"] = category_id
        
        if muscle_ids:
            params["muscles"] = muscle_ids
        
        if equipment_ids:
            params["equipment"] = equipment_ids
        
        return params

    def _run(
        self,
        muscle_ids: Optional[List[int]] = None,
        equipment_ids: Optional[List[int]] = None,
        category_id: Optional[int] = None,
        language_id: int = 2, 
        limit: int = 5, 
        offset: int = 0
    ) -> str:
       raise NotImplementedError("Subclasses must implement this method.")

    async def _arun(
        self,
        muscle_ids: Optional[List[int]] = None,
        equipment_ids: Optional[List[int]] = None,
        category_id: Optional[int] = None,
        language_id: int = 2, 
        limit: int = 5, 
        offset: int = 0
    ) -> str:
        base_url = settings.WGER_API_URL.rstrip('/')
        endpoint = f"{base_url}/exerciseinfo/"
        
        params = self._build_params(
            language_id=language_id,
            muscle_ids=muscle_ids,
            equipment_ids=equipment_ids,
            category_id=category_id,
            limit=limit,
            offset=offset
        )
        headers = {} 

        print(f"[WgerExerciseQueryTool ASYNC] Calling endpoint: {endpoint} with params: {params}")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(endpoint, params=params, headers=headers)
                response.raise_for_status()
                response_json = response.json()

            parsed_response = WgerExerciseInfoResponse.model_validate(response_json)

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

        except httpx.HTTPStatusError as e:
            error_message = f"API Error ASYNC: HTTP {e.response.status_code} - {e.response.text[:500]}"
            print(f"[WgerExerciseQueryTool ASYNC] {error_message}")
            return f"Error: Failed to fetch data from wger API. Status: {e.response.status_code}. Detail: {e.response.text[:100]}"
        except ValidationError as e:
            error_details = f"Pydantic validation error ASYNC for wger response: {e.errors(include_input=False)}"
            print(f"[WgerExerciseQueryTool ASYNC] Validation Error: {error_details}")
            # print(f"[WgerExerciseQueryTool ASYNC] Raw JSON causing validation error: {response_json}")
            return "Error: API response structure from wger is not as expected and could not be processed."
        except Exception as e:
            print(f"[WgerExerciseQueryTool ASYNC] Unexpected error: {type(e).__name__} - {e}")
            return f"Error: An unexpected error occurred while fetching or processing exercise data: {str(e)}"

