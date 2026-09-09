from __future__ import annotations

from run_experiment import _result_paths

from dummy import make_synthetic_pool
from personas import (
    extract_name,
    map_education,
    map_marital,
    map_region,
    row_to_persona,
    select_spread_subset,
)


def test_maps_demographics() -> None:
    assert map_education("초등학교") == "middle"
    assert map_education("고등학교") == "high"
    assert map_education("대학교") == "college"
    assert map_education("대학원") == "graduate"
    assert map_region("광주") == "honam"
    assert map_region("경기") == "capital"
    assert map_region("제주특별자치도") == "gangwon_jeju"
    assert map_marital("미혼") == "Single"
    assert map_marital("배우자있음") == "Married"


def test_extract_name() -> None:
    assert extract_name("전기태 씨는 광주에서 일합니다.", "abc") == "전기태"


def test_row_to_persona() -> None:
    persona = row_to_persona(
        {
            "uuid": "u1",
            "sex": "여자",
            "age": 27,
            "education_level": "대학교",
            "province": "서울",
            "district": "서울-강남구",
            "marital_status": "미혼",
            "occupation": "개발자",
            "family_type": "1인가구",
            "persona": "김민지 씨는 서울에서 소프트웨어를 만듭니다.",
        }
    )
    assert persona is not None
    assert persona.sex == "Female"
    assert persona.age_env == "19-29"
    assert persona.age_birth == "20s"
    assert persona.education == "college"
    assert persona.region == "capital"
    assert persona.cell == ("Female", "19-29", "college", "capital")


def test_spread_subset_covers_each_axis() -> None:
    pool = make_synthetic_pool(per_cell=1)
    subset = select_spread_subset(pool, 20)
    assert len(subset) == 20
    assert len({persona.id for persona in subset}) == 20
    assert len({persona.cell for persona in subset}) == 20
    sexes = {persona.sex for persona in subset}
    ages = {persona.age_env for persona in subset}
    educations = {persona.education for persona in subset}
    regions = {persona.region for persona in subset}
    assert sexes == {"Male", "Female"}
    assert ages == {"19-29", "30-44", "45-59", "60+"}
    assert educations == {"middle", "high", "college", "graduate"}
    assert regions == {
        "capital",
        "yeongnam",
        "honam",
        "chungcheong",
        "gangwon_jeju",
    }
    sex_counts = [sum(p.sex == sex for p in subset) for sex in sexes]
    assert max(sex_counts) - min(sex_counts) <= 1


def test_live_and_dummy_result_paths_differ() -> None:
    dummy_survey, dummy_rooms = _result_paths(True)
    live_survey, live_rooms = _result_paths(False)
    assert dummy_survey.name == "survey.jsonl"
    assert dummy_rooms.name == "rooms.jsonl"
    assert live_survey.name == "survey_qwen.jsonl"
    assert live_rooms.name == "rooms_qwen.jsonl"
