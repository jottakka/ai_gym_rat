import httpx
from typing import List, Optional, Dict, Any
from pydantic import ValidationError

from ai_gym_rat.core.config import settings
from ai_gym_rat.tools.wger_models import WgerExerciseInfoResponse

class WgerAPIClient:
    """
    A client for interacting with the wger (Workout Manager) API.
    Handles HTTP requests and basic response parsing.
    """
    def __init__(self, base_url: Optional[str] = None, language_id: Optional[int] = None):
        self.base_url = (base_url or settings.WGER_API_URL).rstrip('/')
        self.language_id = language_id or settings.WGER_LANGUAGE_ID
        self.api_token = settings.WGER_API_KEY 
        self.default_headers = {
            "Accept": "application/json",
            "Authorization": f"Token {self.api_token}"
        }

    def _build_exercise_info_params(
        self,
        muscle_ids: Optional[List[int]] = None,
        equipment_ids: Optional[List[int]] = None,
        category_id: Optional[int] = None,
        limit: int = 10,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Builds the dictionary of parameters for the /exerciseinfo/ endpoint.
        """
        params: Dict[str, Any] = {
            "language": self.language_id,
            "limit": limit,
            "offset": offset,
            "status": 2
        }
        if category_id is not None:
            params["category"] = category_id
        if muscle_ids:
            params["muscles"] = muscle_ids
        if equipment_ids:
            params["equipment"] = equipment_ids
        return params

    async def get_exercises_info(
        self,
        muscle_ids: Optional[List[int]] = None,
        equipment_ids: Optional[List[int]] = None,
        category_id: Optional[int] = None,
        limit: int = 10,
        offset: int = 0
    ) -> WgerExerciseInfoResponse:
        """
        Fetches a list of exercises with detailed information based on filters.

        Args:
            muscle_ids: List of wger muscle numerical IDs.
            equipment_ids: List of wger equipment numerical IDs.
            category_id: A single wger exercise category numerical ID.
            limit: Maximum number of exercises to fetch.
            offset: Offset for pagination.

        Returns:
            A WgerExerciseInfoResponse object containing the parsed API response.

        Raises:
            httpx.HTTPStatusError: If the API returns an error status code.
            ValidationError: If the API response doesn't match the Pydantic model.
            Exception: For other unexpected errors during the API call.
        """
        endpoint = f"{self.base_url}/exerciseinfo/"
        params = self._build_exercise_info_params(
            muscle_ids=muscle_ids,
            equipment_ids=equipment_ids,
            category_id=category_id,
            limit=limit,
            offset=offset
        )

        print(f"[WgerAPIClient] Fetching exercises from: {endpoint} with params: {params}")

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(endpoint, params=params, headers=self.default_headers)
                response.raise_for_status()
                response_json = response.json()
                
                parsed_response = WgerExerciseInfoResponse.model_validate(response_json)
                return parsed_response
            except httpx.HTTPStatusError as e:
                print(f"[WgerAPIClient] HTTP Error: {e.response.status_code} - {e.response.text[:500]}")
                raise
            except ValidationError as e:
                print(f"[WgerAPIClient] Pydantic Validation Error: {e.errors(include_input=False)}")
                raise
            except Exception as e:
                print(f"[WgerAPIClient] Unexpected error: {type(e).__name__} - {e}")
                raise