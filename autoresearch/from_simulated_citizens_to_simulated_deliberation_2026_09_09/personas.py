"""Census-balanced Korean persona pool from Nemotron-Personas-Korea."""

from __future__ import annotations

import json
import random
import re
from collections import Counter
from collections.abc import Iterator, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

NAME_RE = re.compile(r"^(.{2,5}?)\s*씨")

SEX_MAP = {"남자": "Male", "남": "Male", "여자": "Female", "여": "Female"}

REGION_PREFIXES: tuple[tuple[str, str], ...] = (
    ("서울", "capital"),
    ("인천", "capital"),
    ("경기", "capital"),
    ("부산", "yeongnam"),
    ("대구", "yeongnam"),
    ("울산", "yeongnam"),
    ("경남", "yeongnam"),
    ("경북", "yeongnam"),
    ("경상남", "yeongnam"),
    ("경상북", "yeongnam"),
    ("광주", "honam"),
    ("전남", "honam"),
    ("전북", "honam"),
    ("전라남", "honam"),
    ("전라북", "honam"),
    ("대전", "chungcheong"),
    ("세종", "chungcheong"),
    ("충남", "chungcheong"),
    ("충북", "chungcheong"),
    ("충청남", "chungcheong"),
    ("충청북", "chungcheong"),
    ("강원", "gangwon_jeju"),
    ("제주", "gangwon_jeju"),
)

SEX_LEVELS = ("Male", "Female")
AGE_ENV_LEVELS = ("19-29", "30-44", "45-59", "60+")
EDU_LEVELS = ("middle", "high", "college", "graduate")
REGION_LEVELS = ("capital", "yeongnam", "honam", "chungcheong", "gangwon_jeju")


@dataclass(frozen=True)
class Persona:
    id: str
    name: str
    sex: str
    sex_ko: str
    age: int
    age_env: str
    age_birth: str | None
    education: str
    education_ko: str
    region: str
    region_ko: str
    marital: str | None
    marital_ko: str
    occupation: str
    household: str
    narrative: str

    @property
    def cell(self) -> tuple[str, str, str, str]:
        return (self.sex, self.age_env, self.education, self.region)


def age_env_band(age: int) -> str:
    if age < 30:
        return "19-29"
    if age < 45:
        return "30-44"
    if age < 60:
        return "45-59"
    return "60+"


def age_birth_band(age: int) -> str | None:
    if 19 <= age <= 29:
        return "20s"
    if 30 <= age <= 39:
        return "30s"
    if 40 <= age <= 49:
        return "40s"
    return None


def map_education(value: str) -> str | None:
    text = value.strip()
    if any(token in text for token in ("대학원", "석사", "박사")):
        return "graduate"
    if any(token in text for token in ("전문", "대학", "학사", "4년", "2년")):
        return "college"
    if "고등" in text or text in {"고졸"}:
        return "high"
    if any(token in text for token in ("중학", "초등", "무학", "중졸", "초졸")):
        return "middle"
    return None


def map_region(province: str) -> str | None:
    text = province.strip()
    for prefix, region in REGION_PREFIXES:
        if text.startswith(prefix):
            return region
    return None


def map_marital(value: str) -> str | None:
    text = value.strip()
    if "미혼" in text or "비혼" in text:
        return "Single"
    if "배우자" in text or "기혼" in text:
        return "Married"
    return None


def extract_name(persona_text: str, fallback: str) -> str:
    match = NAME_RE.match(persona_text.strip())
    if match:
        return match.group(1)
    return f"시민-{fallback[:6]}"


def row_to_persona(row: dict[str, Any]) -> Persona | None:
    sex = SEX_MAP.get(str(row.get("sex", "")).strip())
    if sex is None:
        return None
    try:
        age = int(row["age"])
    except (KeyError, TypeError, ValueError):
        return None
    education = map_education(str(row.get("education_level", "")))
    region = map_region(str(row.get("province", "")))
    if education is None or region is None:
        return None
    uuid = str(row.get("uuid") or "")
    if not uuid:
        return None
    narrative = str(row.get("persona") or "").strip()
    if not narrative:
        return None
    occupation = str(row.get("occupation") or "직업 미상").strip()
    household = str(row.get("family_type") or "가구 정보 없음").strip()
    province = str(row.get("province") or "").strip()
    district = str(row.get("district") or "").strip()
    region_ko = f"{province} {district}".strip()
    marital_ko = str(row.get("marital_status") or "").strip()
    return Persona(
        id=uuid,
        name=extract_name(narrative, uuid),
        sex=sex,
        sex_ko=str(row.get("sex") or "").strip(),
        age=age,
        age_env=age_env_band(age),
        age_birth=age_birth_band(age),
        education=education,
        education_ko=str(row.get("education_level") or "").strip(),
        region=region,
        region_ko=region_ko,
        marital=map_marital(marital_ko),
        marital_ko=marital_ko,
        occupation=occupation,
        household=household,
        narrative=narrative,
    )


def iter_source_rows(max_rows: int) -> Iterator[dict[str, Any]]:
    from datasets import load_dataset

    dataset = load_dataset(
        "nvidia/Nemotron-Personas-Korea",
        split=f"train[:{max_rows}]",
    )
    for row in dataset:
        yield dict(row)


def sample_balanced_pool(
    per_cell: int = 1,
    max_rows: int = 80_000,
    seed: int = 20260909,
) -> list[Persona]:
    """Fill every sex x age x education x region cell with `per_cell` personas."""
    target = (
        len(SEX_LEVELS)
        * len(AGE_ENV_LEVELS)
        * len(EDU_LEVELS)
        * len(REGION_LEVELS)
        * per_cell
    )
    buckets: dict[tuple[str, str, str, str], list[Persona]] = {}
    seen: set[str] = set()
    for row in iter_source_rows(max_rows):
        persona = row_to_persona(row)
        if persona is None or persona.id in seen:
            continue
        seen.add(persona.id)
        cell = persona.cell
        bucket = buckets.setdefault(cell, [])
        if len(bucket) >= per_cell:
            continue
        bucket.append(persona)
        filled = sum(len(items) for items in buckets.values())
        if filled >= target and len(buckets) == target // per_cell:
            break
    missing = []
    for sex in SEX_LEVELS:
        for age in AGE_ENV_LEVELS:
            for education in EDU_LEVELS:
                for region in REGION_LEVELS:
                    cell = (sex, age, education, region)
                    if len(buckets.get(cell, [])) < per_cell:
                        missing.append(cell)
    if missing:
        raise RuntimeError(
            f"Could not fill {len(missing)} demographic cells; "
            f"scanned up to {max_rows} rows. First missing: {missing[:5]}"
        )
    pool: list[Persona] = []
    for cell in sorted(buckets):
        pool.extend(buckets[cell][:per_cell])
    # Stable order: cell then id. Seed is reserved for later subsamples.
    _ = seed
    return pool


def save_personas(path: Path, personas: list[Persona]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [asdict(persona) for persona in personas]
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_personas(path: Path) -> list[Persona]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [Persona(**item) for item in raw]


def select_spread_subset(
    personas: Sequence[Persona],
    n: int,
    seed: int = 20260909,
) -> list[Persona]:
    """Pick n personas that spread sex, age, education, and region.

    Each selected persona still occupies a distinct census cell. The greedy
    step prefers the axis levels that currently have the fewest picks, so a
    20-person slice is not clustered in one sex, age band, school level, or
    region.
    """
    if n >= len(personas):
        return list(personas)
    if n <= 0:
        return []
    rng = random.Random(seed)
    remaining = list(personas)
    rng.shuffle(remaining)
    chosen: list[Persona] = []
    while remaining and len(chosen) < n:
        sex_n = Counter(item.sex for item in chosen)
        age_n = Counter(item.age_env for item in chosen)
        edu_n = Counter(item.education for item in chosen)
        region_n = Counter(item.region for item in chosen)

        remaining.sort(
            key=lambda persona, sn=sex_n, an=age_n, en=edu_n, rn=region_n: (
                sn[persona.sex],
                an[persona.age_env],
                en[persona.education],
                rn[persona.region],
                persona.id,
            )
        )
        chosen.append(remaining.pop(0))
    return sorted(chosen, key=lambda persona: (*persona.cell, persona.id))
