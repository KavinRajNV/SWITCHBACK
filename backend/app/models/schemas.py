from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field

class SkillEvidence(BaseModel):
    """
    Evidence record for a single extracted skill.
    """
    skill: str = Field(..., description="Canonical skill name")
    category: str = Field(default="General", description="Skill category")
    confidence: int = Field(..., ge=1, le=10, description="Confidence score from 1 to 10")
    mention_count: int = Field(default=1, ge=1, description="Total mention count across sections")
    found_in_sections: List[str] = Field(default_factory=list, description="List of canonical section types where found")

class LearnerProfile(BaseModel):
    """
    Structured learner profile parsed from resume or manual input.
    """
    raw_sections: Dict[str, str] = Field(default_factory=dict, description="Raw extracted document sections")
    extracted_skills: List[SkillEvidence] = Field(default_factory=list, description="List of extracted skill evidence records")
    experience_years_est: Optional[float] = Field(default=None, description="Estimated total years of professional experience")
    parse_warnings: List[str] = Field(default_factory=list, description="Degraded/recoverable parse warning messages")

class GoalProfile(BaseModel):
    """
    Learner goal profile parsed from free-text goal prompt.
    """
    target_role: Optional[str] = Field(default=None, description="Matched target occupation title")
    target_soc_code: Optional[str] = Field(default=None, description="O*NET SOC code for target role")
    timeframe_days: Optional[int] = Field(default=None, description="Parsed target timeframe in days")
    hours_per_week: Optional[int] = Field(default=None, description="Parsed commitment in hours per week")
    background_hint: Optional[str] = Field(default=None, description="Unconsumed background text hint")
    needs_clarification: bool = Field(default=False, description="Flag indicating target role requires user clarification")

class Milestone(BaseModel):
    """
    Single step in a learning path.
    """
    skill: str = Field(..., description="Target skill for this milestone")
    step_number: int = Field(..., ge=1, description="Sequential step number 1..N")
    cost: float = Field(..., description="Graph transition cost weight")
    reachable_via: Optional[str] = Field(default=None, description="Source skill used to reach this milestone")
    is_essential: bool = Field(default=True, description="Whether this skill is essential for the target role")

class SkillContribution(BaseModel):
    """
    Per-skill SHAP contribution or importance explanation.
    """
    skill: str = Field(..., description="Canonical skill name")
    contribution_lpa: float = Field(..., description="SHAP contribution or market value impact in LPA")
    explanation: str = Field(..., description="Natural language explanation sentence")

class QAResponse(BaseModel):
    """
    Structured response from the constrained Q&A engine.
    """
    question_id: str = Field(..., description="Identifier of the canned question answered")
    answer_text: str = Field(..., description="Natural language answer text")
    structured_payload: Optional[Dict[str, Any]] = Field(default=None, description="Optional structured data payload (e.g. course lists)")
