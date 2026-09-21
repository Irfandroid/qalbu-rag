from app.safety.guardrails import SafetyGuardrails, SafetyLevel


def test_immediate_danger_triggered():
    assert SafetyGuardrails().check("Aku ingin bunuh diri").level == SafetyLevel.IMMEDIATE_DANGER
    assert (
        SafetyGuardrails().check("Aku ingin menyakiti diri").level == SafetyLevel.IMMEDIATE_DANGER
    )


def test_normal_reflection_not_blocked():
    assert SafetyGuardrails().check("Aku bingung dengan tujuan hidup").level == SafetyLevel.NORMAL


def test_crisis_detector_normalizes_slang_typos_and_leetspeak():
    guard = SafetyGuardrails()
    assert guard.check("aku mau bundir").level == SafetyLevel.IMMEDIATE_DANGER
    assert guard.check("aku ingin matiii").level == SafetyLevel.IMMEDIATE_DANGER
    assert guard.check("I want to d1e").level == SafetyLevel.IMMEDIATE_DANGER


def test_crisis_detector_keeps_clear_hard_negative_normal():
    guard = SafetyGuardrails()
    assert guard.check("aku tidak ingin bunuh diri").level == SafetyLevel.NORMAL
    assert guard.check("artikel tentang suicide").level == SafetyLevel.NORMAL
