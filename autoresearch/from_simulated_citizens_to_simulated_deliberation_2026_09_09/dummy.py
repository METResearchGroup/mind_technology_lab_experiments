"""Offline personas and a chat client that follows the paper's JSON contracts."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Sequence

from client import ChatResult
from paper_tables import PAPER_TABLE3
from personas import (
    AGE_ENV_LEVELS,
    EDU_LEVELS,
    REGION_LEVELS,
    SEX_LEVELS,
    Persona,
    age_birth_band,
)
from questions import QUESTION_BY_ID

_NAME_RE = re.compile(r"당신은 (.+?)입니다")

SEX_KO = {"Male": "남자", "Female": "여자"}
AGE_MID = {"19-29": 24, "30-44": 37, "45-59": 52, "60+": 67}
EDU_KO = {
    "middle": "중학교",
    "high": "고등학교",
    "college": "대학교",
    "graduate": "대학원",
}
REGION_KO = {
    "capital": "서울 강남구",
    "yeongnam": "부산 해운대구",
    "honam": "광주 서구",
    "chungcheong": "대전 유성구",
    "gangwon_jeju": "강원 춘천시",
}
GIVEN = (
    "민지",
    "서준",
    "하은",
    "도윤",
    "수아",
    "지호",
    "예린",
    "준서",
    "소율",
    "현우",
    "채원",
    "시우",
    "다은",
    "건우",
    "유나",
    "태윤",
)


def make_synthetic_pool(per_cell: int = 1) -> list[Persona]:
    """Fill every sex x age x education x region cell without a Hub download."""
    pool: list[Persona] = []
    index = 0
    for sex in SEX_LEVELS:
        for age_env in AGE_ENV_LEVELS:
            for education in EDU_LEVELS:
                for region in REGION_LEVELS:
                    for cell_i in range(per_cell):
                        age = AGE_MID[age_env] + cell_i
                        name = GIVEN[index % len(GIVEN)]
                        sex_ko = SEX_KO[sex]
                        education_ko = EDU_KO[education]
                        region_ko = REGION_KO[region]
                        marital = "Single" if age < 35 else "Married"
                        marital_ko = "미혼" if marital == "Single" else "배우자있음"
                        occupation = (
                            "사무직"
                            if education
                            in {
                                "college",
                                "graduate",
                            }
                            else "서비스직"
                        )
                        household = "1인가구" if marital == "Single" else "부부와 거주"
                        narrative = (
                            f"{name} 씨는 {region_ko}에 사는 {age}세 {sex_ko}입니다. "
                            f"학력은 {education_ko}이고 직업은 {occupation}입니다. "
                            f"{household}."
                        )
                        pool.append(
                            Persona(
                                id=f"synth-{sex}-{age_env}-{education}-{region}-{cell_i}",
                                name=name,
                                sex=sex,
                                sex_ko=sex_ko,
                                age=age,
                                age_env=age_env,
                                age_birth=age_birth_band(age),
                                education=education,
                                education_ko=education_ko,
                                region=region,
                                region_ko=region_ko,
                                marital=marital,
                                marital_ko=marital_ko,
                                occupation=occupation,
                                household=household,
                                narrative=narrative,
                            )
                        )
                        index += 1
    return pool


def _topic_rate(user: str) -> float:
    for question in QUESTION_BY_ID.values():
        if question.topic_ko in user:
            return PAPER_TABLE3[question.id]["full"] / 100.0
    return 0.5


def _pick_index(key: str, rate: float) -> int:
    digest = hashlib.sha256(key.encode()).hexdigest()
    unit = int(digest[:8], 16) / 0xFFFFFFFF
    return 0 if unit < rate else 1


class DummyClient:
    """Deterministic stand-in that returns parseable Korean JSON."""

    def chat(
        self,
        messages: Sequence[dict[str, str]],
        *,
        temperature: float,
        max_tokens: int,
        seed: int | None = None,
    ) -> ChatResult:
        user = messages[-1]["content"]
        system = messages[0]["content"] if messages else ""
        key = f"{system}\n{user}\n{temperature}\n{seed}"
        if '"choice"' in user:
            rate = _topic_rate(user)
            a_text = b_text = None
            for question in QUESTION_BY_ID.values():
                if question.topic_ko in user:
                    a_text = question.position_a.ko
                    b_text = question.position_b.ko
                    break
            if a_text and b_text:
                text = a_text if _pick_index(key, rate) == 0 else b_text
                payload = f'{{"choice": "{text}"}}'
            else:
                payload = '{"choice": "A"}'
        else:
            match = _NAME_RE.search(user)
            name = match.group(1) if match else "시민"
            payload = (
                f'{{"public": "{name}은 이 쟁점에서 근거를 들어 말합니다. '
                f"상대 입장의 비용도 인정하지만, 지금 고른 쪽이 더 "
                f'타당하다고 봅니다."}}'
            )
        _ = max_tokens
        return ChatResult(
            text=payload,
            raw=payload,
            prompt_tokens=0,
            completion_tokens=12,
            elapsed_sec=0.0,
        )
