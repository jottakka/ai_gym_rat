import re
from typing import List, Optional
from pydantic import BaseModel, Field, model_validator

class WgerTranslation(BaseModel):
    name: str
    description: str
    language: int

class WgerCategoryInfo(BaseModel):
    id: int
    name: str

class WgerMuscleInfo(BaseModel):
    id: int
    name: str  # Native language name
    name_en: Optional[str] = None
    is_front: bool

class WgerEquipmentInfo(BaseModel):
    id: int
    name: str

class WgerExerciseInfo(BaseModel):
    id: int
    uuid: str
    
    # These fields will be populated by the model_validator
    name: Optional[str] = Field(default=None, description="Name of the exercise, preferably in English.")
    description: Optional[str] = Field(default=None, description="Description of the exercise, preferably in English and with HTML tags removed.")
    category_name: Optional[str] = Field(default=None, description="Category of the exercise.")
    primary_muscles: List[str] = Field(default_factory=list, description="List of primary muscles targeted, using English names if available.")
    secondary_muscles: List[str] = Field(default_factory=list, description="List of secondary muscles targeted, using English names if available.")
    equipment_required: List[str] = Field(default_factory=list, description="List of equipment required for the exercise.")

    # Raw data fields from API, aliased to match JSON keys.
    # These are processed by the validator.
    translations_data: List[WgerTranslation] = Field(alias="translations")
    category_data: WgerCategoryInfo = Field(alias="category")
    muscles_data: List[WgerMuscleInfo] = Field(alias="muscles")
    muscles_secondary_data: List[WgerMuscleInfo] = Field(alias="muscles_secondary", default_factory=list)
    equipment_data: List[WgerEquipmentInfo] = Field(alias="equipment", default_factory=list)


    @model_validator(mode='after')
    def process_api_data(self) -> 'WgerExerciseInfo':
        english_translation = None
        # Find English translation (language ID 2)
        for t in self.translations_data:
            if t.language == 2:
                english_translation = t
                break
        
        if english_translation:
            self.name = english_translation.name
            if english_translation.description:
                # Remove HTML tags from description
                clean_desc = re.sub(r'<[^>]+>', '', english_translation.description)
                self.description = clean_desc.strip()
        elif self.translations_data:  # Fallback to the first available translation
            first_translation = self.translations_data[0]
            self.name = first_translation.name
            if first_translation.description:
                clean_desc = re.sub(r'<[^>]+>', '', first_translation.description)
                self.description = clean_desc.strip()

        if self.category_data:
            self.category_name = self.category_data.name
        
        if self.muscles_data:
            self.primary_muscles = [m.name_en if m.name_en else m.name for m in self.muscles_data]

        if self.muscles_secondary_data:
            self.secondary_muscles = [m.name_en if m.name_en else m.name for m in self.muscles_secondary_data]

        if self.equipment_data:
            self.equipment_required = [e.name for e in self.equipment_data]
            
        return self

    class Config:
        populate_by_name = True # Important for alias usage


class WgerExerciseInfoResponse(BaseModel):
    results: List[WgerExerciseInfo]