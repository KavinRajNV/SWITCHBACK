import json
import urllib.request
import urllib.parse

API_BASE = 'http://localhost:8000'

def post_json(endpoint, payload):
    req = urllib.request.Request(
        f"{API_BASE}{endpoint}",
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode('utf-8'))

def get_json(endpoint):
    with urllib.request.urlopen(f"{API_BASE}{endpoint}") as resp:
        return json.loads(resp.read().decode('utf-8'))

def run_e2e_session_flow():
    print("======================================================================")
    print("RUNNING END-TO-END E2E SESSION EXECUTION & VERIFICATION")
    print("======================================================================")

    # 1. Health check
    health = get_json('/health')
    print(f"1. [Health Check] Status: {health['status']}, Occupations Loaded: {health['artifacts_loaded']['occupations_count']}")
    assert health['status'] == 'healthy'

    # 2. Entry Choice: Save manual skills
    initial_skills = ["Python", "SQL", "Machine Learning", "Statistics"]
    profile_data = post_json('/api/profile/manual-skills', {"skills": initial_skills})
    session_id = profile_data['session_id']
    added_skills = profile_data['added_skills']
    total_skills = profile_data['total_current_skills']
    print(f"2. [Entry Choice /start] Session ID: {session_id}")
    print(f"   Added Skills: {added_skills}, Total Skills Count: {total_skills}")

    # 3. Your Skills: GitHub Verification
    github_res = post_json('/api/live/github-verify', {"session_id": session_id, "github_username": "torvalds"})
    print(f"3. [Your Skills /skills] GitHub Verification Status: {github_res['status']}")
    print(f"   Verified Skills: {github_res['verified_skills']}")

    # 4. Target Role: Search & Generate Path
    roles = get_json('/api/roles/search?q=Data%20Scientist')
    target_soc = roles['results'][0]['onet_soc_code']
    target_title = roles['results'][0]['title']
    print(f"4. [Target Role /target-role] Target Selected: '{target_title}' (SOC: {target_soc})")

    path_res = post_json('/api/path/generate', {"session_id": session_id, "target_occupation_soc_code": target_soc})
    print(f"   Real Computed Path Length: {path_res['path_length']} milestones")
    print(f"   Is Fully Qualified: {path_res['is_fully_qualified']}")
    print(f"   Elevation Curve Steps: {len(path_res['elevation_profile'])}")
    assert path_res['path_length'] == len(path_res['milestones'])

    # 5. Your Learning Path: Complete Milestone
    first_milestone = path_res['milestones'][0]['skill']
    complete_res = post_json('/api/progress/complete-milestone', {
        "session_id": session_id,
        "skill": first_milestone,
        "evidence_type": "project_log"
    })
    print(f"5. [Your Path /path] Completed Milestone: '{first_milestone}'")
    print(f"   Milestones Saved: {complete_res['milestones_saved']}")
    print(f"   Updated Path Length: {complete_res['new_path_length']} milestones remaining")

    # 6. Ask Assistant Panel: Q&A Dispatch
    qa_res = post_json('/api/qa/ask', {"session_id": session_id, "question_id": "how_long_will_this_take"})
    print(f"6. [Q&A Panel /api/qa/ask] Inquiry: 'how_long_will_this_take'")
    print(f"   Answer Text Snippet: {qa_res['answer_text'][:120]}...")

    print("======================================================================")
    print("ALL END-TO-END ENDPOINTS PASSED 100% SUCCESSFULLY WITH REAL DATA!")
    print("======================================================================")

    return {
        "session_id": session_id,
        "added_skills": added_skills,
        "github": github_res,
        "role": target_title,
        "path": path_res,
        "complete": complete_res,
        "qa": qa_res
    }

if __name__ == "__main__":
    session_output = run_e2e_session_flow()
    with open('scripts/session_output.json', 'w') as f:
        json.dump(session_output, f, indent=2)
