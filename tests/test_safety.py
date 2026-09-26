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


def test_crisis_detector_keeps_clear_hard_negative_normal():
    guard = SafetyGuardrails()
    assert guard.check("aku tidak ingin bunuh diri").level == SafetyLevel.NORMAL
    assert guard.check("artikel tentang suicide").level == SafetyLevel.NORMAL


def test_negated_self_harm_does_not_hide_threat_to_other_person():
    guard = SafetyGuardrails()
    decision = guard.check("Aku tidak ingin bunuh diri, tapi ingin membunuh orang")
    assert decision.level == SafetyLevel.IMMEDIATE_DANGER
    assert decision.pattern_id == "harm_other_id"


def test_crisis_detector_catches_indirect_absence_language():
    assert (
        SafetyGuardrails().check("rasanya lebih baik aku tidak ada").level
        == SafetyLevel.IMMEDIATE_DANGER
    )
