import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parents[2]
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.db.mongo_client import get_db
from app.ml.path_sequencer import generate_path, get_graph

def run_smoke_tests():
    db = get_db()
    graph = get_graph()

    # Find SOC codes
    ds_occ = db.occupations_enriched.find_one({"title": {"$regex": "Data Scientist", "$options": "i"}})
    de_occ = db.occupations_enriched.find_one({"title": {"$regex": "Database Architect", "$options": "i"}}) or db.occupations_enriched.find_one({"title": {"$regex": "Software Developer", "$options": "i"}})
    swe_occ = db.occupations_enriched.find_one({"title": {"$regex": "Software Developer", "$options": "i"}})

    ds_soc = ds_occ["onet_soc_code"] if ds_occ else "15-2051.00"
    de_soc = de_occ["onet_soc_code"] if de_occ else "15-1252.00"
    swe_soc = swe_occ["onet_soc_code"] if swe_occ else "15-1252.00"

    print("======================================================================")
    print("SMOKE TEST SCENARIO 1: {Excel, SQL, Business Analysis} -> Data Scientist")
    print(f"Target SOC: {ds_soc} ({ds_occ['title'] if ds_occ else 'Data Scientist'})")
    path1 = generate_path({"Excel", "SQL", "Business Analysis"}, ds_soc, graph)
    print(f"Generated Path Length: {len(path1)} milestones")
    print("First 15 Milestones:")
    for m in path1[:15]:
        print(f"  Step {m['step_number']:2d}: {m['skill']:<30} (cost: {m['cost']:.4f}, via: {m['reachable_via']})")

    print("\n======================================================================")
    print("SMOKE TEST SCENARIO 2A: {Python, SQL} -> Data Scientist")
    print(f"Target SOC: {ds_soc} ({ds_occ['title'] if ds_occ else 'Data Scientist'})")
    path2a = generate_path({"Python", "SQL"}, ds_soc, graph)
    print(f"Generated Path Length: {len(path2a)} milestones")
    print("First 15 Milestones:")
    for m in path2a[:15]:
        print(f"  Step {m['step_number']:2d}: {m['skill']:<30} (cost: {m['cost']:.4f}, via: {m['reachable_via']})")

    print("\n======================================================================")
    print("SMOKE TEST SCENARIO 2B: {Python, SQL} -> Software Developer / Data Engineer")
    print(f"Target SOC: {swe_soc} ({swe_occ['title'] if swe_occ else 'Software Developer'})")
    path2b = generate_path({"Python", "SQL"}, swe_soc, graph)
    print(f"Generated Path Length: {len(path2b)} milestones")
    print("First 15 Milestones:")
    for m in path2b[:15]:
        print(f"  Step {m['step_number']:2d}: {m['skill']:<30} (cost: {m['cost']:.4f}, via: {m['reachable_via']})")

    print("\n======================================================================")
    print("SMOKE TEST SCENARIO 3: Empty Skill Set {} -> Data Scientist (Cold Start)")
    path3 = generate_path(set(), ds_soc, graph)
    print(f"Generated Path Length: {len(path3)} milestones")
    print("First 15 Milestones:")
    for m in path3[:15]:
        print(f"  Step {m['step_number']:2d}: {m['skill']:<30} (cost: {m['cost']:.4f}, via: {m['reachable_via']})")
    print("======================================================================")

if __name__ == "__main__":
    run_smoke_tests()
