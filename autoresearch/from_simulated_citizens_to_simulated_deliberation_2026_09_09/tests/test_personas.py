from __future__ import annotations

from personas import (
    extract_name,
    map_education,
    map_marital,
    map_region,
    row_to_persona,
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
