// Backend dev server port. Override with VITE_API_BASE_URL (see frontend/.env.example).
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8011';

export interface SkillEvidence {
  skill: string;
  found_in_sections: string[];
  mention_count: number;
  confidence: number;
}

export interface LearnerProfile {
  session_id?: string;
  extracted_skills: SkillEvidence[];
  raw_skills_list?: string[];
  experience_years_est?: number;
  total_skills_count?: number;
}

export interface GoalProfile {
  target_role?: string;
  target_soc_code?: string;
  timeframe_days?: number;
  hours_per_week?: number;
  background_hint?: string;
  needs_clarification: boolean;
}

export interface TargetOccupation {
  onet_soc_code: string;
  title: string;
  market_role_id?: string;
  market_median_salary_lpa?: number;
  market_posting_count?: number;
}

export interface Course {
  title: string;
  source: string;
  url: string;
  is_paid?: boolean;
  price?: number;
  rating?: number;
}

export interface Milestone {
  step_number: number;
  skill: string;
  cost: number;
  reachable_via?: string;
  is_essential: boolean;
  explanation?: string;
  free_courses?: Course[];
  paid_courses?: Course[];
}

export interface ElevationPoint {
  step: number;
  skill: string;
  cumulative_predicted_salary_lpa: number;
}

export interface PathResponse {
  session_id: string;
  target_occupation_soc_code: string;
  target_occupation_title: string;
  target_market_role_id?: string;
  is_fully_qualified: boolean;
  path_length: number;
  milestones: Milestone[];
  owned_skill_contributions: Array<{ skill: string; contribution_lpa: number; explanation: string }>;
  elevation_profile: ElevationPoint[];
}

export interface CompleteMilestoneResponse {
  session_id: string;
  completed_skill: string;
  evidence_type: string;
  confidence_assigned: number;
  milestones_saved: number;
  previous_path_length: number;
  new_path_length: number;
  remaining_milestones: Milestone[];
}

export interface QAResponse {
  question_id: string;
  answer_text: string;
  structured_payload?: any;
}

export interface DashboardResponse {
  session_id: string;
  profile_summary: {
    total_acquired_skills: number;
    experience_years_est?: number | null;
    current_predicted_salary_lpa: number;
  };
  target_role: {
    onet_soc_code: string | null;
    title: string | null;
    market_median_salary_lpa?: number | null;
  };
  progress: {
    completed_milestones_count: number;
    remaining_milestones_count: number;
    progress_percentage: number;
  };
  next_action_milestone: Milestone | null;
  elevation_profile: ElevationPoint[];
  recent_activities: Array<{ skill: string; evidence_type: string; completed_at: string; confidence?: number }>;
}

// 1. Health check
export async function checkHealth() {
  const res = await fetch(`${API_BASE_URL}/health`);
  return res.json();
}

// Lightweight reachability probe for the "backend offline" banner.
export async function pingBackend(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE_URL}/health`, { signal: AbortSignal.timeout(4000) });
    return res.ok;
  } catch {
    return false;
  }
}

// 2. Upload Resume
export async function uploadResume(file: File): Promise<{ session_id: string; learner_profile: LearnerProfile; parse_warnings: string[] }> {
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch(`${API_BASE_URL}/api/profile/from-resume`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to parse resume.');
  }

  const data = await res.json();
  return {
    session_id: data.session_id,
    learner_profile: data.learner_profile,
    parse_warnings: data.parse_warnings || [],
  };
}

// 3. Manual Skills
export async function saveManualSkills(
  skills: Array<{ skill: string; confidence: number }> | string[],
  session_id?: string
): Promise<{ session_id: string; learner_profile: LearnerProfile }> {
  // Normalise: accept plain strings (confidence defaults to 5) or {skill, confidence} objects
  const skillsPayload = (skills as any[]).map((s) =>
    typeof s === 'string' ? { skill: s, confidence: 5 } : s
  );

  const res = await fetch(`${API_BASE_URL}/api/profile/manual-skills`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ skills: skillsPayload, session_id }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to save manual skills.');
  }

  const data = await res.json();
  const learner_profile: LearnerProfile = data.learner_profile || {
    session_id: data.session_id,
    extracted_skills: (data.added_skills || skillsPayload.map((s) => s.skill)).map(
      (sk: string, i: number) => ({
        skill: sk,
        found_in_sections: ['MANUAL'],
        mention_count: 1,
        confidence: skillsPayload[i]?.confidence ?? 5,
      })
    ),
    raw_skills_list: data.added_skills || skillsPayload.map((s) => s.skill),
    total_skills_count: data.total_current_skills || skillsPayload.length,
  };

  return { session_id: data.session_id, learner_profile };
}

// 4. Goal Text Parser
export async function parseGoalText(goal_text: string, session_id?: string): Promise<{ session_id: string; learner_profile: LearnerProfile; goal_profile: GoalProfile; target_occupation?: TargetOccupation }> {
  const res = await fetch(`${API_BASE_URL}/api/profile/from-goal-text`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ goal_text, session_id }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to parse goal text.');
  }

  const data = await res.json();
  // Do NOT fall back to hardcoded Python/SQL — return an empty skill list so the
  // SkillsScreen shows no pre-populated skills (goal text input has no claimed skills).
  const learner_profile: LearnerProfile = data.learner_profile || {
    session_id: data.session_id,
    extracted_skills: [],
    total_skills_count: 0,
  };

  // Build target_occupation from goal_profile if the backend didn't return one separately
  let target_occupation: TargetOccupation | undefined = data.target_occupation;
  if (!target_occupation && data.goal_profile?.target_role && data.goal_profile?.target_soc_code) {
    target_occupation = {
      onet_soc_code: data.goal_profile.target_soc_code,
      title: data.goal_profile.target_role,
    };
  }

  return {
    session_id: data.session_id,
    learner_profile,
    goal_profile: data.goal_profile,
    target_occupation,
  };
}

// 5. Search Skills Autocomplete
export async function searchSkills(query: string): Promise<string[]> {
  if (!query || query.trim().length < 1) return [];
  const res = await fetch(`${API_BASE_URL}/api/skills/search?q=${encodeURIComponent(query)}`);
  if (!res.ok) return [];
  const data = await res.json();
  return data.results || [];
}

// 6. Search Occupations Autocomplete
export async function searchRoles(query: string): Promise<TargetOccupation[]> {
  if (!query || query.trim().length < 1) return [];
  const res = await fetch(`${API_BASE_URL}/api/roles/search?q=${encodeURIComponent(query)}`);
  if (!res.ok) return [];
  const data = await res.json();
  return data.results || [];
}

// 7. Generate Path
export async function generatePath(session_id: string, target_occupation_soc_code?: string, target_market_role_id?: string): Promise<PathResponse> {
  const res = await fetch(`${API_BASE_URL}/api/path/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id, target_occupation_soc_code, target_market_role_id }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to generate learning path.');
  }

  return res.json();
}

// 8. Complete Milestone
export async function completeMilestone(session_id: string, completed_skill: string, evidence_type: 'self_report' | 'project_log' | 'github_verified'): Promise<CompleteMilestoneResponse> {
  const res = await fetch(`${API_BASE_URL}/api/progress/complete-milestone`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id, skill: completed_skill, evidence_type }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to complete milestone.');
  }

  return res.json();
}

// 9. GitHub Skill Verification
export async function verifyGithub(session_id: string, github_username: string): Promise<{ status: string; github_username: string; verified_skills: string[]; total_current_skills: number }> {
  const res = await fetch(`${API_BASE_URL}/api/live/github-verify`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id, github_username }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'GitHub verification failed.');
  }

  return res.json();
}

// 10. Ask Assistant Q&A
export async function askQA(session_id: string, question_id: string, extra_skill?: string, milestone_index?: number): Promise<QAResponse> {
  const res = await fetch(`${API_BASE_URL}/api/qa/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id, question_id, extra_skill, milestone_index }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Q&A inquiry failed.');
  }

  return res.json();
}

export interface RelatedRole {
  onet_soc_code: string;
  title: string;
  index: number;
  relatedness_tier: string;
  market_median_salary_lpa?: number;
}

export interface RelatedRolesResponse {
  soc_code: string;
  count: number;
  related_occupations: RelatedRole[];
}

export interface JobPosting {
  title: string;
  company: string;
  location: string;
  salary_min?: number;
  salary_max?: number;
  url: string;
  source: string;
}

export interface LiveJobsResponse {
  status: string;
  role: string;
  jobs: JobPosting[];
  total_found?: number;
}

// 11. Get Related Occupations (O*NET Primary-Short)
export async function getRelatedRoles(soc_code: string): Promise<RelatedRolesResponse> {
  const res = await fetch(`${API_BASE_URL}/api/roles/${encodeURIComponent(soc_code)}/related`);
  if (!res.ok) {
    return { soc_code, count: 0, related_occupations: [] };
  }
  return res.json();
}

// 12. Get Dashboard Data
export async function getDashboardData(session_id: string): Promise<DashboardResponse> {
  const res = await fetch(`${API_BASE_URL}/api/dashboard?session_id=${encodeURIComponent(session_id)}`);
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to fetch dashboard data.');
  }
  return res.json();
}

// 13. Get Live Jobs Strip (Adzuna)
export async function getLiveJobs(role: string): Promise<LiveJobsResponse> {
  const res = await fetch(`${API_BASE_URL}/api/live/jobs?role=${encodeURIComponent(role)}`);
  if (!res.ok) {
    return { status: 'unavailable', role, jobs: [] };
  }
  return res.json();
}

// 14. Get Recommended Roles (P6)
export interface RecommendedRole {
  onet_soc_code: string;
  title: string;
  market_role_id?: string;
  overlap_count: number;
  jaccard_score: number;
  idf_weighted_score?: number;
  match_score?: number;
  market_median_salary_lpa?: number;
  matched_skills: string[];
}

export async function getRecommendedRoles(session_id: string): Promise<RecommendedRole[]> {
  const res = await fetch(`${API_BASE_URL}/api/roles/recommended?session_id=${encodeURIComponent(session_id)}`);
  if (!res.ok) return [];
  const data = await res.json();
  return data.recommendations || [];
}
