from __future__ import annotations

from lifemem.types import SurveyQuestion


def qa_to_statements(question: str, answer_text: str) -> tuple[str, str]:
    """Rule-based survey-to-statement conversion (paper uses gpt-3.5-turbo-0125)."""

    q = question.strip().rstrip("?")
    answer = answer_text.strip().rstrip(".")
    lowered = q[:1].lower() + q[1:] if q else q
    second = f"You answered '{answer}' to the question '{lowered}'."
    first = f"I answered '{answer}' to the question '{lowered}'."
    return second, first


def profile_paragraph(fields: dict[str, str]) -> str:
    sex = fields["sex"]
    ses = fields["ses"]
    education = fields["education"]
    religion = fields["religion"]
    region = fields["region"]
    birth_year = fields["birth_year"]
    occupation = fields["occupation"]
    return (
        f"You are {sex}. You were born in {birth_year}. You live in {region}. "
        f"Your education level is {education}. You work as {occupation}. "
        f"You identify as {religion}. Your socioeconomic status is {ses}."
    )


def option_block(question: SurveyQuestion) -> str:
    lines = ["Question:", question.question, "", "Options:"]
    for option in question.options:
        lines.append(f"{option.code}: {option.text}")
    lines.append("")
    lines.append(
        "Answer with exactly one option number. Do not provide any explanation."
    )
    return "\n".join(lines)
