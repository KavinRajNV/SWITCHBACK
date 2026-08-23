import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from pymongo.database import Database

from app.db.mongo_client import get_db
from app.models.schemas import LearnerProfile, GoalProfile

COLLECTION_NAME = "learner_sessions"

def create_session(
    learner_profile: Optional[LearnerProfile] = None,
    goal_profile: Optional[GoalProfile] = None,
    target_soc: Optional[str] = None,
    current_skills: Optional[List[str]] = None,
    db: Optional[Database] = None
) -> str:
    """
    Creates a new learner session in Mongo collection 'learner_sessions' and returns generated session_id (UUID4).
    """
    if db is None:
        db = get_db()

    session_id = str(uuid.uuid4())
    now_iso = datetime.now().isoformat()

    lp_dict = learner_profile.model_dump() if learner_profile else LearnerProfile().model_dump()
    gp_dict = goal_profile.model_dump() if goal_profile else GoalProfile().model_dump()

    # Initial current_skills extracted from learner profile if not passed explicitly
    if current_skills is None:
        current_skills = [se["skill"] for se in lp_dict.get("extracted_skills", [])]

    if not target_soc and goal_profile and goal_profile.target_soc_code:
        target_soc = goal_profile.target_soc_code

    doc = {
        "session_id": session_id,
        "created_at": now_iso,
        "updated_at": now_iso,
        "learner_profile": lp_dict,
        "goal_profile": gp_dict,
        "current_skills": list(set(current_skills)),
        "target_occupation_soc_code": target_soc,
        "completed_milestones": [],
        "stored_path": []
    }

    db[COLLECTION_NAME].insert_one(doc)
    return session_id

def get_session(session_id: str, db: Optional[Database] = None) -> Optional[Dict[str, Any]]:
    """
    Retrieves a session document by session_id.
    """
    if not session_id or not isinstance(session_id, str):
        return None

    if db is None:
        db = get_db()

    doc = db[COLLECTION_NAME].find_one({"session_id": session_id}, {"_id": 0})
    return doc

def update_session(session_id: str, updates: Dict[str, Any], db: Optional[Database] = None) -> bool:
    """
    Updates fields on a session document by session_id.
    """
    if not session_id or not updates:
        return False

    if db is None:
        db = get_db()

    updates["updated_at"] = datetime.now().isoformat()
    res = db[COLLECTION_NAME].update_one({"session_id": session_id}, {"$set": updates})
    return res.matched_count > 0
