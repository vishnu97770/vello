"""
Wake word detection accuracy test suite.

Tests is_wake_word() against the full matrix from the engineering spec.
Run with:   python tests/test_wake_word.py
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from vello.stt.vosk_stt import is_wake_word, WAKE_SIMILARITY_THRESHOLD

# ── Test matrix ───────────────────────────────────────────────────────────────

SHOULD_WAKE = [
    # Ideal input
    ("hey vello",       True,  "ideal"),
    ("vello",           True,  "ideal"),
    # Vosk phonetic substitutions (confirmed real misrecognitions)
    ("hey velo",        True,  "Vosk alias — closest phonetic match"),
    ("hey bello",       True,  "Vosk alias — b/v confusion"),
    ("hey fellow",      True,  "confirmed Vosk substitution"),
    ("hey yellow",      True,  "borderline — document score"),
    ("hey cello",       True,  "Vosk alias"),
    ("hey mellow",      True,  "Vosk alias"),
    # Other wake words in grammar
    ("jarvis",          True,  "alternate wake"),
    ("hey jarvis",      True,  "alternate wake"),
    ("hey buddy",       True,  "alternate wake"),
    # Confirmed Vosk substitutions for "hey vello" — MUST wake
    ("hey well",        True,  "Vosk substitution for 'hey vello' — must wake"),
    # Case / spacing tolerance
    ("HEY VELLO",       True,  "uppercase"),
    ("  hey velo  ",    True,  "leading/trailing whitespace"),
]

SHOULD_NOT_WAKE = [
    # These are Vosk hallucinations too far from "hey vello" to accept
    ("hey there little",     False, "phonetically too distant"),
    ("hey the law",          False, "phonetically too distant"),
    ("hey were law",         False, "phonetically too distant"),
    ("hey there know",       False, "phonetically too distant"),
    # Common ambient speech
    ("hello world",          False, "ambient"),
    ("good morning",         False, "ambient"),
    ("play some music",      False, "ambient"),
    ("what time is it",      False, "ambient"),
    # Short noise words
    ("the",                  False, "noise"),
    ("um",                   False, "noise"),
    ("hey",                  False, "noise — 'hey' alone must not wake"),
    # Phonetically distant
    ("hello there",          False, "too distant"),
    ("hey yellow submarine", False, "too distant"),
]


def run_tests():
    print(f"\n{'═'*60}")
    print(f" WAKE WORD TEST SUITE")
    print(f" Threshold: {WAKE_SIMILARITY_THRESHOLD}")
    print(f"{'═'*60}\n")

    tp = fp = tn = fn = 0
    failures = []

    # ── True positives ────────────────────────────────────────────
    print("SHOULD WAKE (true positives):")
    print(f"  {'Input':<30} {'Score':>6}  {'Expected':>6}  {'Result'}")
    print(f"  {'-'*60}")
    for text, expected, note in SHOULD_WAKE:
        matched, score = is_wake_word(text)
        result = "PASS" if matched == expected else "FAIL"
        flag   = "✓" if result == "PASS" else "✗"
        print(f"  {flag} {repr(text):<30} {score:>5.0f}%  {'WAKE':>6}  {result}  ({note})")
        if matched:
            tp += 1
        else:
            fn += 1
            failures.append(("FN", text, score, note))

    # ── True negatives ────────────────────────────────────────────
    print(f"\nSHOULD NOT WAKE (true negatives):")
    print(f"  {'Input':<30} {'Score':>6}  {'Expected':>8}  {'Result'}")
    print(f"  {'-'*60}")
    for text, expected, note in SHOULD_NOT_WAKE:
        matched, score = is_wake_word(text)
        result = "PASS" if matched == expected else "FAIL"
        flag   = "✓" if result == "PASS" else "✗"
        print(f"  {flag} {repr(text):<30} {score:>5.0f}%  {'IGNORE':>8}  {result}  ({note})")
        if not matched:
            tn += 1
        else:
            fp += 1
            failures.append(("FP", text, score, note))

    # ── Summary ───────────────────────────────────────────────────
    total_pos = tp + fn
    total_neg = tn + fp

    tpr = (tp / total_pos * 100) if total_pos else 0.0
    fpr = (fp / total_neg * 100) if total_neg else 0.0

    print(f"\n{'─'*60}")
    print(f" Threshold used:              {WAKE_SIMILARITY_THRESHOLD}")
    print(f" True positive rate (recall): {tpr:.1f}%  (target: >95%)")
    print(f" False positive rate:         {fpr:.1f}%  (target: <2%)")
    print(f" Passes: {tp + tn} / {total_pos + total_neg}")

    if failures:
        print(f"\n FAILURES ({len(failures)}):")
        for kind, text, score, note in failures:
            print(f"   {kind}: '{text}' score={score:.0f}%  ({note})")
    else:
        print("\n All tests passed.")

    print(f"{'═'*60}\n")

    # Exit non-zero if recall below 95% or FPR above 2%
    if tpr < 95.0 or fpr > 2.0:
        print("RESULT: FAILED — accuracy targets not met")
        sys.exit(1)
    print("RESULT: PASSED")


if __name__ == "__main__":
    run_tests()
