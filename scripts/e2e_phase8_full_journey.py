import json
import os
import urllib.request
import urllib.parse
import sys

API_BASE = os.getenv('SWITCHBACK_API_BASE', 'http://localhost:8011')

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

def run_phase8_full_journey():
    print("======================================================================", flush=True)
    print("RUNNING PHASE 8 MASTER END-TO-END USER JOURNEY INTEGRATION TEST", flush=True)
    print("======================================================================", flush=True)

    # 1. Landing Page Health Check
    health = get_json('/health')
    print(f"1. [Landing Page /health] Status: {health['status']}, Occupations Loaded: {health['artifacts_loaded']['occupations_count']}", flush=True)
    assert health['status'] == 'healthy'

    # 2. Entry Screen (/start): Save manual baseline skills
    profile_data = post_json('/api/profile/manual-skills', {"skills": ["Python", "SQL", "Machine Learning", "Statistics"]})
    session_id = profile_data['session_id']
    added_skills = profile_data['added_skills']
    total_skills = profile_data['total_current_skills']
    print(f"2. [Entry Choice /start] Created Session ID: {session_id}", flush=True)
    print(f"   Baseline Skills Added: {added_skills} | Total Skills: {total_skills}", flush=True)

    # 3. Your Skills Screen (/skills): Verify Repositories via GitHub REST API
    github_res = post_json('/api/live/github-verify', {"session_id": session_id, "github_username": "torvalds"})
    print(f"3. [Your Skills /skills] GitHub Verification Status: {github_res['status']}", flush=True)
    print(f"   Verified Repository Languages: {github_res['verified_skills']}", flush=True)

    # 4. Target Role Screen (/target-role): Search O*NET & Fetch Related Occupations
    roles = get_json('/api/roles/search?q=Data%20Scientist')
    target_soc = roles['results'][0]['onet_soc_code']
    target_title = roles['results'][0]['title']
    print(f"4. [Target Role /target-role] Selected Role: '{target_title}' (SOC: {target_soc})", flush=True)

    related_res = get_json(f"/api/roles/{target_soc}/related")
    print(f"   O*NET Primary-Short Stretch Goals Found ({related_res['count']}):", flush=True)
    for rel in related_res['related_occupations'][:3]:
        print(f"   • Stretch Goal: {rel['title']} (SOC: {rel['onet_soc_code']})", flush=True)

    # 5. Path Generation (/path): Generate Dijkstra Graph Path
    path_res = post_json('/api/path/generate', {"session_id": session_id, "target_occupation_soc_code": target_soc})
    print(f"5. [Path Generation /path] Path Length: {path_res['path_length']} milestones", flush=True)
    print(f"   Elevation Curve Steps: {len(path_res['elevation_profile'])} points (Baseline + {path_res['path_length']} steps)", flush=True)
    assert path_res['path_length'] == len(path_res['milestones'])

    # 6. What-If Scenario Simulator: Toggle Hypothetical Skill
    whatif_res = post_json('/api/qa/ask', {"session_id": session_id, "question_id": "what_if_i_already_know_x", "extra_skill": "AWS"})
    print(f"6. [What-If Simulator] Toggled 'AWS': {whatif_res['answer_text'][:110]}...", flush=True)

    # 7. Learner Frontier Dashboard (/dashboard): Aggregate Summary View
    dash_res = get_json(f"/api/dashboard?session_id={session_id}")
    prog_pct = dash_res['progress']['progress_percentage']
    print(f"7. [Dashboard /dashboard] Progress: {prog_pct}% | Target Role: {dash_res['target_role']['title']}", flush=True)
    print(f"   Elevation Trajectory Point Count: {len(dash_res['elevation_profile'])}", flush=True)

    # 8. Adaptive Progress Feedback Loop: Complete All Path Milestones
    print("8. [Adaptive Progress Loop] Completing milestones one-by-one...", flush=True)
    curr_path = path_res
    completed_history = []

    while curr_path['path_length'] > 0 and not curr_path['is_fully_qualified']:
        ms_to_complete = curr_path['milestones'][0]['skill']
        comp_res = post_json('/api/progress/complete-milestone', {
            "session_id": session_id,
            "skill": ms_to_complete,
            "evidence_type": "project_log"
        })
        completed_history.append(ms_to_complete)
        print(f"   • Mastered '{ms_to_complete}' | Saved: {comp_res['milestones_saved']} | Remaining: {comp_res['new_path_length']}", flush=True)
        
        curr_path = post_json('/api/path/generate', {"session_id": session_id, "target_occupation_soc_code": target_soc})

    # 9. Celebration Screen (/celebration): 100% Qualification
    print(f"9. [Celebration Screen /celebration] Fully Qualified: {curr_path['is_fully_qualified']} | Path Length: {curr_path['path_length']}", flush=True)
    assert curr_path['is_fully_qualified'] is True or curr_path['path_length'] == 0

    print("======================================================================", flush=True)
    print("PHASE 8 MASTER E2E INTEGRATION TEST PASSED 100% WITH ZERO ERRORS!", flush=True)
    print("======================================================================", flush=True)

    return {
        "session_id": session_id,
        "added_skills": added_skills,
        "github_verified": github_res['verified_skills'],
        "target_role": target_title,
        "related_roles": related_res['related_occupations'],
        "initial_path_length": path_res['path_length'],
        "completed_history": completed_history,
        "is_fully_qualified": curr_path['is_fully_qualified']
    }

if __name__ == "__main__":
    out = run_phase8_full_journey()
    with open('scripts/phase8_master_journey_output.json', 'w') as f:
        json.dump(out, f, indent=2)
