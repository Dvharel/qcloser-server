from .models import CallRecording


def build_analysis_email(recording: CallRecording) -> tuple[str, str]:
    subject = f"{recording.deal_title or f'Recording #{recording.id}'} — Analysis Report"
    body = (recording.analysis_json or {}).get("analysis_text", "")
    if not body:
        raise ValueError(
            f"analysis_text is empty or missing for recording {recording.id}"
        )
    return subject, body


def _fmt(label: str, data: dict) -> str:
    """'Label: assessment. notes' — returns empty string if both fields are blank."""
    assessment = (data.get("assessment") or "").strip()
    notes = (data.get("notes") or "").strip()
    if not assessment and not notes:
        return ""
    parts = []
    if assessment:
        parts.append(assessment if assessment.endswith(".") else assessment + ".")
    if notes:
        parts.append(notes)
    return f"{label}: {' '.join(parts)}"


def build_feedback_email(recording: CallRecording) -> tuple[str, str]:
    if not recording.feedback_json:
        raise ValueError(f"feedback_json is empty or missing for recording {recording.id}")

    fj = recording.feedback_json
    title = recording.deal_title or f"Recording #{recording.id}"
    subject = f"{title} — Feedback Report"

    sections = []

    # ── SPIN Execution Quality ─────────────────────────────────────────────────
    spin = fj.get("spin_execution_quality") or {}
    spin_lines = [
        _fmt("Situation questions",   spin.get("situation_questions")   or {}),
        _fmt("Problem questions",     spin.get("problem_questions")     or {}),
        _fmt("Implication questions", spin.get("implication_questions") or {}),
        _fmt("Need-payoff questions", spin.get("need_payoff_questions") or {}),
    ]
    spin_lines = [l for l in spin_lines if l]
    if spin_lines:
        sections.append("SPIN Execution Quality\n\n" + "\n\n".join(spin_lines))

    # ── Value Development ──────────────────────────────────────────────────────
    vd = fj.get("value_development") or {}
    vd_lines = [
        _fmt("Seriousness",            vd.get("seriousness")            or {}),
        _fmt("Urgency",                vd.get("urgency")                or {}),
        _fmt("Buyer verbalized value", vd.get("buyer_verbalized_value") or {}),
    ]
    vd_lines = [l for l in vd_lines if l]
    if vd_lines:
        sections.append("Value Development\n\n" + "\n\n".join(vd_lines))

    # ── Commitment Strategy ────────────────────────────────────────────────────
    cs = fj.get("commitment_strategy") or {}
    cs_lines = [
        _fmt("Pushed too early",   cs.get("pushed_too_early")  or {}),
        _fmt("Realistic advance",  cs.get("realistic_advance") or {}),
        _fmt("Next step clear",    cs.get("next_step_clear")   or {}),
    ]
    cs_lines = [l for l in cs_lines if l]
    if cs_lines:
        sections.append("Commitment Strategy\n\n" + "\n\n".join(cs_lines))

    # ── Objection Handling ─────────────────────────────────────────────────────
    obj = fj.get("objection_prevention_vs_reaction") or {}
    obj_assessment = (obj.get("assessment") or "").strip()
    obj_notes = (obj.get("notes") or "").strip()
    if obj_assessment or obj_notes:
        parts = []
        if obj_assessment:
            parts.append(obj_assessment if obj_assessment.endswith(".") else obj_assessment + ".")
        if obj_notes:
            parts.append(obj_notes)
        sections.append("Objection Handling\n\n" + " ".join(parts))

    # ── Coaching for Next Call ─────────────────────────────────────────────────
    coaching = fj.get("specific_coaching") or {}
    missing_qs = [q for q in (coaching.get("missing_questions") or []) if q]
    improve    = [i for i in (coaching.get("improve_next_call") or []) if str(i).strip()]
    keep       = [k for k in (coaching.get("keep_doing")        or []) if str(k).strip()]

    if missing_qs or improve or keep:
        coaching_lines = ["Coaching for Next Call", ""]
        if missing_qs:
            coaching_lines.append("Questions to add:")
            for item in missing_qs:
                q      = (item.get("question")      or "").strip()
                better = (item.get("better_version") or "").strip()
                if q:
                    coaching_lines.append(
                        f'- {q} → Better: "{better}"' if better else f"- {q}"
                    )
            coaching_lines.append("")
        if improve:
            coaching_lines.append("Things to improve:")
            for item in improve:
                coaching_lines.append(f"- {str(item).strip()}")
            coaching_lines.append("")
        if keep:
            coaching_lines.append("Keep doing:")
            for item in keep:
                coaching_lines.append(f"- {str(item).strip()}")
        sections.append("\n".join(coaching_lines).rstrip())

    body = "\n\n---\n\n".join(sections)
    return subject, body


def build_followup_email(recording: CallRecording) -> tuple[str, str]:
    if not recording.followup_json:
        raise ValueError(f"followup_json is empty or missing for recording {recording.id}")

    fj = recording.followup_json
    title = recording.deal_title or f"Recording #{recording.id}"
    subject = f"{title} — Follow-up"

    sections = []

    # ── Message to client ──────────────────────────────────────────────────────
    message = (fj.get("message") or "").strip()
    if message:
        sections.append(f"Message to client:\n{message}")

    # ── Brief for rep ──────────────────────────────────────────────────────────
    brief = (fj.get("brief_for_rep") or "").strip()
    if brief:
        sections.append(f"Brief for rep:\n{brief}")

    # ── Next steps ─────────────────────────────────────────────────────────────
    next_steps = [s for s in (fj.get("next_steps") or []) if str(s).strip()]
    if next_steps:
        numbered = "\n".join(f"{i}. {str(s).strip()}" for i, s in enumerate(next_steps, 1))
        sections.append(f"Next steps:\n{numbered}")

    # ── Questions to ask on next call ──────────────────────────────────────────
    questions = [q for q in (fj.get("questions_to_ask") or []) if str(q).strip()]
    if questions:
        numbered = "\n".join(f"{i}. {str(q).strip()}" for i, q in enumerate(questions, 1))
        sections.append(f"Questions to ask on next call:\n{numbered}")

    # ── Suggested closing lines ────────────────────────────────────────────────
    closing = [l for l in (fj.get("lines_to_close") or []) if str(l).strip()]
    if closing:
        numbered = "\n".join(f"{i}. {str(l).strip()}" for i, l in enumerate(closing, 1))
        sections.append(f"Suggested closing lines:\n{numbered}")

    body = "\n\n---\n\n".join(sections)
    return subject, body
