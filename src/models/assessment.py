"""Assessment data models using Pydantic."""

from typing import List, Dict
from pydantic import BaseModel, Field

class ProcStep(BaseModel):
    """Processing step model."""
    process: str = ""
    amount: float = 0.0
    co2e_per_unit: float = 0.0
    unit: str = ""

class Assessment(BaseModel):
    """Main assessment data model."""
    lifetime_weeks: int = 52
    selected_materials: List[str] = Field(default_factory=list)
    material_masses: Dict[str, float] = Field(default_factory=dict)
    processing_data: Dict[str, List[ProcStep]] = Field(default_factory=dict)

    def model_dump(self) -> dict:
        """Convert to dictionary format compatible with session state."""
        result = {
            "lifetime_weeks": self.lifetime_weeks,
            "selected_materials": self.selected_materials,
            "material_masses": self.material_masses,
            "processing_data": {}
        }
        
        # Convert ProcStep objects to dicts
        for material, steps in self.processing_data.items():
            result["processing_data"][material] = [
                step.model_dump() if hasattr(step, 'model_dump') else step 
                for step in steps
            ]
        
        return result