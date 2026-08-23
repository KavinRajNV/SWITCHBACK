def explain_owned_skill(skill: str, shap_contribution: float) -> str:
    """
    Generates natural language explanation for an owned skill's per-profile SHAP contribution.
    """
    val = float(shap_contribution)

    if val >= 0.05:
        return f"Your {skill} experience is contributing an estimated +₹{val:.2f}L to your predicted market salary benchmark."
    elif val <= -0.05:
        return f"Your {skill} profile signals are associated with a slight market adjustment of -₹{abs(val):.2f}L relative to general role averages."
    else:
        return f"Your {skill} experience provides core foundational competency with a neutral direct salary adjustment (+₹{val:.2f}L)."

def explain_gap_skill(skill: str, global_importance_rank: int, global_importance_value: float, total_skills: int = 265) -> str:
    """
    Generates natural language explanation for a target gap skill using global SHAP importance rank and value.
    """
    rank = int(global_importance_rank)
    val = float(global_importance_value)

    if rank <= 10:
        tier_str = "top-tier high-impact requirement"
    elif rank <= 30:
        tier_str = "key industry skill requirement"
    else:
        tier_str = "specialized technical capability"

    return f"Acquiring {skill} ranks #{rank} out of {total_skills} skills by market salary impact ({tier_str}, average impact: ₹{val:.2f}L)."
