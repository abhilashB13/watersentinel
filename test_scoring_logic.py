"""
Run this with: python test_scoring_logic.py

Direct, isolated tests against calculate_quality_score() — no server, no
API, no browser needed. Tests the actual Python function with known input
combinations and asserts the expected output, catching logic bugs (like
the bathing-status contradiction and category-mislabeling bugs found via
manual UI testing) systematically, in seconds, rather than one screenshot
at a time.

This is NOT exhaustive — it's a growing regression suite. Add a new test
function every time a new bug is found via manual testing, so it can never
silently reappear.
"""

import sys
import importlib.util
from pathlib import Path

project_root = Path(__file__).parent

# FIXED: importing via `from agents.water_profiler.tools import ...` triggers
# Python to first execute agents/__init__.py, which eagerly imports the full
# ADK orchestrator chain (agent.py -> RAG -> ChromaDB) — even though this
# test only needs the pure-Python calculate_quality_score() function and has
# no actual dependency on ADK, ChromaDB, or any external package. Loading
# tools.py directly via importlib bypasses the package __init__ chain
# entirely, so this test runs with ZERO dependency on chromadb/ADK being
# installed — genuinely isolated, as intended.
tools_path = project_root / "agents" / "water_profiler" / "tools.py"
spec = importlib.util.spec_from_file_location("water_profiler_tools", tools_path)
tools_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tools_module)
calculate_quality_score = tools_module.calculate_quality_score

PASS = "✅ PASS"
FAIL = "❌ FAIL"
results = []


def check(name, condition, detail=""):
    status = PASS if condition else FAIL
    results.append((status, name, detail))
    print(f"{status}  {name}" + (f"  — {detail}" if detail and status == FAIL else ""))


# ─────────────────────────────────────────────────────────────────────────
print("=" * 75)
print("TEST 1 — Bathing status must be UNSAFE if ANY symptom demands it,")
print("regardless of which symptom produces the lowest numeric score")
print("=" * 75)

result = calculate_quality_score(
    contaminants=[], severity="medium", source_type="borewell",
    symptoms=["egg_smell", "skin_irritation", "vessel_staining", "stomach_issues", "salty_taste"],
    frequent_sickness=True, affected_count="2-3", since_when="weeks",
)
check(
    "Bathing status is 'unsafe' when skin_irritation is present, even though "
    "vessel_staining alone would produce a lower score with bathing=safe",
    result["bathing_status"] == "unsafe",
    f"got bathing_status={result['bathing_status']!r} (this is the exact bug from the screenshot)",
)

# ─────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 75)
print("TEST 2 — Category must trace to the ACTUAL triggering symptom,")
print("not be inferred purely from the numeric score range")
print("=" * 75)

result2 = calculate_quality_score(
    contaminants=[], severity="medium", source_type="borewell",
    symptoms=["egg_smell", "skin_irritation", "vessel_staining", "stomach_issues", "salty_taste"],
    frequent_sickness=True, affected_count="2-3", since_when="weeks",
)
check(
    "Category should NOT be 'iron' when no iron/yellow-water symptom was reported "
    "(previous bug: score landed in iron's numeric range purely by coincidence)",
    result2["primary_category"] != "iron",
    f"got primary_category={result2['primary_category']!r}",
)
check(
    "Category should be 'h2s' since egg_smell is the actual most-severe reported symptom",
    result2["primary_category"] == "h2s",
    f"got primary_category={result2['primary_category']!r}",
)

# ─────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 75)
print("TEST 3 — Sewage smell must ALWAYS produce score 0, unsafe both,")
print("regardless of source type (municipal vs borewell vs open well)")
print("=" * 75)

for source in ["municipal_pipeline", "borewell", "hand_pump", "open_well"]:
    r = calculate_quality_score(
        contaminants=[], severity="high", source_type=source, symptoms=["sewage_smell"],
    )
    check(
        f"Sewage smell on {source}: score must be 0",
        r["quality_score"] == 0,
        f"got score={r['quality_score']}",
    )
    check(
        f"Sewage smell on {source}: drinking AND bathing must both be unsafe",
        r["drinking_status"] == "unsafe" and r["bathing_status"] == "unsafe",
        f"got drinking={r['drinking_status']!r} bathing={r['bathing_status']!r}",
    )

# ─────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 75)
print("TEST 4 — Diagnosed disease is its OWN category (medical_emergency),")
print("never folded into generic 'sewage', and is source-independent")
print("=" * 75)

r4 = calculate_quality_score(
    contaminants=[], severity="high", source_type="municipal_pipeline",
    symptoms=["egg_smell"], diagnosed_disease=True,
)
check(
    "Diagnosed disease produces primary_category = 'medical_emergency', not 'sewage'",
    r4["primary_category"] == "medical_emergency",
    f"got {r4['primary_category']!r}",
)
check(
    "Diagnosed disease forces score to 0 regardless of other milder symptoms present",
    r4["quality_score"] == 0,
    f"got score={r4['quality_score']}",
)

# ─────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 75)
print("TEST 5 — The ORIGINAL false-positive bug: municipal + egg smell + salty")
print("taste + stomach issues, diagnosed_disease=False, must NOT trigger")
print("faecal/coliform score-0")
print("=" * 75)

r5 = calculate_quality_score(
    contaminants=[], severity="medium", source_type="municipal_pipeline",
    symptoms=["egg_smell", "salty_taste", "stomach_issues"],
    diagnosed_disease=False, frequent_sickness=True,
)
check(
    "Score must be in a plausible H2S-driven range (30-55), NOT 0",
    30 <= r5["quality_score"] <= 55,
    f"got score={r5['quality_score']}",
)
check(
    "Category must NOT be 'sewage' or 'medical_emergency' — no such symptom/diagnosis was reported",
    r5["primary_category"] not in ("sewage", "medical_emergency"),
    f"got {r5['primary_category']!r}",
)

# ─────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 75)
print("TEST 6 — TDS tiering matches BIS/WHO thresholds exactly")
print("=" * 75)

print("Testing on municipal_pipeline (baseline=85) — chosen because borewell's")
print("baseline (65) is already below several TDS fixed-scores, so baseline")
print("correctly wins there regardless of the bug — municipal's higher baseline")
print("(85) properly isolates whether TDS-vs-baseline comparison works.")

tds_cases = [
    (250, True, "safe"),      # within optimal range, no deduction, baseline holds
    (450, True, "safe"),      # within BIS acceptable, no deduction, baseline holds
    (700, True, "caution"),   # fixed TDS score 85 TIES baseline 85 exactly — no visible score drop, but bathing still correctly flags caution
    (1000, False, "caution"), # fixed TDS score 70 < baseline 85 -> TDS genuinely wins, must show as deduction
    (1500, False, "caution"), # fixed TDS score 55 < baseline 85 -> deduction
    (2500, False, "caution"), # fixed TDS score 40 < baseline 85 -> deduction
]
for tds, expect_no_deduction, expect_bathing in tds_cases:
    r = calculate_quality_score(
        contaminants=[], severity="low", source_type="municipal_pipeline", symptoms=[], tds_value=tds,
    )
    if expect_no_deduction:
        check(f"TDS {tds}ppm: no deduction, score stays at baseline (85)", r["quality_score"] == 85,
              f"got score={r['quality_score']}")
    else:
        check(f"TDS {tds}ppm: deduction applied, score below baseline (85)", r["quality_score"] < 85,
              f"got score={r['quality_score']}")
    check(f"TDS {tds}ppm: bathing_status = {expect_bathing!r}", r["bathing_status"] == expect_bathing,
          f"got bathing_status={r['bathing_status']!r}")

# ─────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 75)
print("TEST 7 — Source-type baseline holds when NO symptoms reported")
print("=" * 75)

baselines = {"municipal_pipeline": 85, "borewell": 65, "hand_pump": 55, "open_well": 45}
for source, expected in baselines.items():
    r = calculate_quality_score(contaminants=[], severity="low", source_type=source, symptoms=[])
    check(f"{source}: baseline score = {expected}", r["quality_score"] == expected,
          f"got {r['quality_score']}")

# ─────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 75)
print("TEST 8 — A real measured TDS reading must NEVER score better than the")
print("source-type baseline (the original 'reporting less scores better' bug)")
print("=" * 75)

for source, baseline_val in [("municipal_pipeline", 85), ("borewell", 65)]:
    r = calculate_quality_score(
        contaminants=[], severity="low", source_type=source, symptoms=[], tds_value=1500,
    )
    check(
        f"{source}: real TDS 1500ppm reading must score <= baseline ({baseline_val}), never better",
        r["quality_score"] <= baseline_val,
        f"got score={r['quality_score']} (baseline={baseline_val})",
    )

# ─────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 75)
print("TEST 9 — Category selection must ignore descriptive-text false")
print("positives (e.g. vessel_staining's label mentioning 'iron' as context")
print("must NOT misclassify it as the iron contaminant type)")
print("=" * 75)

r9 = calculate_quality_score(
    contaminants=[], severity="medium", source_type="borewell",
    symptoms=["vessel_staining"],  # no actual iron/yellow_colour symptom reported
)
check(
    "vessel_staining alone must NOT produce category='iron' "
    "(its descriptive label mentions 'iron' as context only, not as the actual symptom)",
    r9["primary_category"] != "iron",
    f"got primary_category={r9['primary_category']!r}",
)

# ─────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 75)
print("TEST 10 — Multiple contaminant types present: priority order must be")
print("deterministic and consistent (sewage > black > iron > h2s > high_tds)")
print("=" * 75)

r10 = calculate_quality_score(
    contaminants=[], severity="high", source_type="borewell",
    symptoms=["iron", "egg_smell"],  # both iron and h2s present
)
check(
    "When both iron and h2s symptoms are present, category follows fixed priority order (iron wins)",
    r10["primary_category"] == "iron",
    f"got primary_category={r10['primary_category']!r}",
)

# ─────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 75)
print("TEST 11 — Low-confidence AI photo findings must NOT silently")
print("contribute symptoms to scoring (confidence-gating check)")
print("=" * 75)

try:
    photo_module_path = project_root / "agents" / "water_profiler" / "photo_analyzer.py"
    spec2 = importlib.util.spec_from_file_location("photo_analyzer", photo_module_path)
    photo_module = importlib.util.module_from_spec(spec2)
    spec2.loader.exec_module(photo_module)

    low_confidence_result = {
        "success": True, "is_water_photo": True, "confidence": 35,  # below threshold
        "water_colour": "yellow", "visible_sediment": False,
        "visible_foam_or_bubbles": False, "visible_oily_sheen": False,
    }
    symptoms_extracted = photo_module.photo_findings_to_symptoms(low_confidence_result)
    check(
        "Low-confidence (35%) photo finding must NOT produce any symptoms — "
        "honest non-detection, not a silently-scored guess",
        symptoms_extracted == [],
        f"got symptoms={symptoms_extracted!r}",
    )

    high_confidence_result = {**low_confidence_result, "confidence": 85}
    symptoms_extracted_high = photo_module.photo_findings_to_symptoms(high_confidence_result)
    check(
        "High-confidence (85%) photo finding DOES produce symptoms",
        len(symptoms_extracted_high) > 0,
        f"got symptoms={symptoms_extracted_high!r}",
    )
except FileNotFoundError:
    print("  (skipped — photo_analyzer.py not found at expected path, apply GPS/confidence patch first)")

# ─────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 75)
passed = sum(1 for s, _, _ in results if s == PASS)
failed = sum(1 for s, _, _ in results if s == FAIL)
print(f"RESULTS: {passed} passed, {failed} failed, out of {len(results)} checks")
print("=" * 75)

if failed > 0:
    print("\n⚠️  FAILING CHECKS — these indicate real bugs still present:")
    for status, name, detail in results:
        if status == FAIL:
            print(f"  - {name}: {detail}")
    sys.exit(1)
else:
    print("\n✅ All checks passed.")
    sys.exit(0)
