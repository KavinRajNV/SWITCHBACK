import json
import urllib.request
import urllib.parse
import sys

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

def run_phase7_e2e_flow():
    print("======================================================================", flush=True)
    print("RUNNING PHASE 7 END-TO-END WHAT-IF, DASHBOARD & COMPLETION TEST", flush=True)
    print("======================================================================", flush=True)

    # 1. Health check & Task 2 Related Occupations Endpoint
    health = get_json('/health')
    print(f"1. [Health Check] Status: {health['status']}", flush=True)

    related_res = get_json('/api/roles/15-2051.00/related')
    print(f"2. [Task 2 /api/roles/15-2051.00/related] Found {related_res['count']} O*NET Primary-Short occupations:", flush=True)
    for rel in related_res['related_occupations']:
        print(f"   • {rel['title']} (SOC: {rel['onet_soc_code']}, Index: {rel['index']})", flush=True)
    assert related_res['count'] >= 3

    # Empty SOC check
    empty_rel = get_json('/api/roles/99-9999.00/related')
    print(f"   [Task 2 Empty Check 99-9999.00] Count: {empty_rel['count']}, Array: {empty_rel['related_occupations']}", flush=True)
    assert empty_rel['count'] == 0

    # 3. Create Session & Skills
    profile_res = post_json('/api/profile/manual-skills', {"skills": ["Python", "SQL", "Machine Learning"]})
    session_id = profile_res['session_id']
    print(f"3. [Session Init] Created Session ID: {session_id}", flush=True)

    # 4. Generate Path
    path_res = post_json('/api/path/generate', {"session_id": session_id, "target_occupation_soc_code": "15-2051.00"})
    initial_length = path_res['path_length']
    print(f"4. [Path Generation] Initial Path Length: {initial_length} milestones", flush=True)

    # 5. What-If Simulation
    whatif_res = post_json('/api/qa/ask', {"session_id": session_id, "question_id": "what_if_i_already_know_x", "extra_skill": "AWS"})
    print(f"5. [Task 1 What-If Simulator] Toggled 'AWS': {whatif_res['answer_text'][:100]}...", flush=True)
    if whatif_res.get('structured_payload'):
        print(f"   Payload: Original {whatif_res['structured_payload'].get('original_path_length')} -> New {whatif_res['structured_payload'].get('new_path_length')}", flush=True)

    # 6. Dashboard Aggregate View
    dash_res = get_json(f"/api/dashboard?session_id={session_id}")
    prog_pct = dash_res['progress']['progress_percentage']
    target_role_title = dash_res['target_role']['title']
    print(f"6. [Task 3 Dashboard /api/dashboard] Progress Pct: {prog_pct}%, Target Role: {target_role_title}", flush=True)

    # 7. Complete ALL Milestones until 100% Qualification (Task 4)
    print("7. [Task 4 Full Completion Flow] Completing milestones one-by-one...", flush=True)
    curr_path = path_res
    completed_skills = []
    
    while curr_path['path_length'] > 0 and not curr_path['is_fully_qualified']:
        ms_to_complete = curr_path['milestones'][0]['skill']
        comp_res = post_json('/api/progress/complete-milestone', {
            "session_id": session_id,
            "skill": ms_to_complete,
            "evidence_type": "project_log"
        })
        completed_skills.append(ms_to_complete)
        print(f"   • Completed '{ms_to_complete}' | Milestones Saved: {comp_res['milestones_saved']} | Remaining: {comp_res['new_path_length']}", flush=True)

        # Re-fetch path
        curr_path = post_json('/api/path/generate', {"session_id": session_id, "target_occupation_soc_code": "15-2051.00"})

    print(f"   Final State -> is_fully_qualified: {curr_path['is_fully_qualified']}, remaining milestones: {curr_path['path_length']}", flush=True)
    assert curr_path['is_fully_qualified'] is True or curr_path['path_length'] == 0

    print("======================================================================", flush=True)
    print("PHASE 7 END-TO-END VERIFICATION PASSED 100% SUCCESSFULLY!", flush=True)
    print("======================================================================", flush=True)

    return {
        "session_id": session_id,
        "related_roles": related_res,
        "what_if": whatif_res,
        "dash": dash_res,
        "final_path": curr_path,
        "completed_skills": completed_skills
    }

if __name__ == "__main__":
    out = run_phase7_e2e_flow()
    with open('scripts/phase7_session_output.json', 'w') as f:
        json.dump(out, f, indent=2)
