import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parents[2]
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from typing import Dict, Any, List, Set, Tuple
from app.db.mongo_client import get_db
from app.nlp.parse_resume import parse_resume
from app.data_pipeline.skill_matcher import SkillMatcher

def validate_resume_ner() -> Dict[str, Any]:
    """
    Evaluates section-detection + skill-confidence pipeline against all 220 records in 'resume_ner_training'.
    Computes precision, recall, and F1 metrics across ground-truth 'Skills' entity annotations.
    """
    db = get_db()
    matcher = SkillMatcher.from_mongo(db)

    docs = list(db.resume_ner_training.find({}))
    if not docs:
        raise ValueError("No records found in 'resume_ner_training' collection!")

    total_tp = 0
    total_fp = 0
    total_fn = 0

    examples: List[Dict[str, Any]] = []

    for idx, doc in enumerate(docs):
        content = doc.get("content", "")
        annotations = doc.get("annotation", [])

        # Extract ground truth skills from annotation entities labeled 'Skills'
        gt_skills_canonical: Set[str] = set()
        for ann in annotations:
            label_list = ann.get("label", [])
            if "Skills" in label_list:
                for text_span in ann.get("points", []):
                    span_text = text_span.get("text", "").strip()
                    if span_text:
                        d = matcher.match_direct(span_text)
                        if d:
                            gt_skills_canonical.add(d.skill)
                        else:
                            extracted = matcher.extract_skills(span_text)
                            for m in extracted:
                                gt_skills_canonical.add(m.skill)

        # Run pipeline
        profile = parse_resume(content.encode("utf-8"), file_type="text", matcher=matcher)
        pred_skills_canonical = set(se.skill for se in profile.extracted_skills)

        # Micro-averaged TP, FP, FN
        tp = len(pred_skills_canonical.intersection(gt_skills_canonical))
        fp = len(pred_skills_canonical - gt_skills_canonical)
        fn = len(gt_skills_canonical - pred_skills_canonical)

        total_tp += tp
        total_fp += fp
        total_fn += fn

        # Collect sample side-by-side examples
        if len(examples) < 3 and len(gt_skills_canonical) >= 3:
            examples.append({
                "record_id": str(doc.get("_id")),
                "content_snippet": content[:150].replace("\n", " "),
                "ground_truth_skills": sorted(list(gt_skills_canonical)),
                "predicted_skills": sorted(list(pred_skills_canonical)),
                "tp": tp,
                "fp": fp,
                "fn": fn
            })

    precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
    recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    metrics = {
        "num_records": len(docs),
        "total_true_positives": total_tp,
        "total_false_positives": total_fp,
        "total_false_negatives": total_fn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "sample_examples": examples
    }

    print("======================================================================")
    print("RESUME NER VALIDATION RESULTS (220 Records):")
    print(f"  - Total Records Evaluated : {len(docs)}")
    print(f"  - True Positives (TP)     : {total_tp}")
    print(f"  - False Positives (FP)    : {total_fp}")
    print(f"  - False Negatives (FN)    : {total_fn}")
    print(f"  - Precision               : {precision * 100:.2f}%")
    print(f"  - Recall                  : {recall * 100:.2f}%")
    print(f"  - F1 Score                : {f1 * 100:.2f}%")
    print("======================================================================")

    for i, ex in enumerate(examples, 1):
        safe_snippet = ex['content_snippet'].encode('ascii', errors='ignore').decode('ascii')
        print(f"\n--- Side-by-Side Example {i} ---")
        print(f"Snippet      : {safe_snippet}...")
        print(f"Ground Truth : {ex['ground_truth_skills']}")
        print(f"Predicted    : {ex['predicted_skills']}")

    return metrics

if __name__ == "__main__":
    validate_resume_ner()
