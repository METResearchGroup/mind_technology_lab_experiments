"""Policy questions, Korean/English wordings, and human survey benchmarks."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Position:
    key: str
    en: str
    ko: str


@dataclass(frozen=True)
class Question:
    id: str
    domain: str
    topic_en: str
    topic_ko: str
    position_a: Position
    position_b: Position
    human_overall: float
    human_by_group: dict[str, dict[str, float]] = field(default_factory=dict)
    axes: tuple[str, ...] = ()


# Human A-shares from arXiv:2609.07573 Appendix A (Tables 8-15), as percentages.
QUESTIONS: tuple[Question, ...] = (
    Question(
        id="env_priority",
        domain="environment",
        topic_en="Environmental policy priority",
        topic_ko="환경 정책의 우선순위",
        position_a=Position(
            key="A",
            en=(
                "Environmental protection first "
                "(even if economic growth slows somewhat)"
            ),
            ko="환경 보호를 우선한다 (경제성장이 다소 둔화되더라도)",
        ),
        position_b=Position(
            key="B",
            en="Economic growth first (even if the environment is somewhat harmed)",
            ko="경제성장을 우선한다 (환경이 다소 훼손되더라도)",
        ),
        human_overall=68.0,
        axes=("sex", "age_env", "education", "region"),
        human_by_group={
            "sex": {"Male": 57, "Female": 80},
            "age_env": {"19-29": 51, "30-44": 58, "45-59": 75, "60+": 81},
            "education": {
                "middle": 87,
                "high": 73,
                "college": 65,
                "graduate": 68,
            },
            "region": {
                "capital": 69,
                "yeongnam": 64,
                "honam": 73,
                "chungcheong": 70,
                "gangwon_jeju": 69,
            },
        },
    ),
    Question(
        id="env_means",
        domain="environment",
        topic_en="Means of solving environmental problems",
        topic_ko="환경 문제 해결 수단",
        position_a=Position(
            key="A",
            en="Stronger penalties and law enforcement",
            ko="처벌과 법집행을 강화한다",
        ),
        position_b=Position(
            key="B",
            en="Voluntary efforts by citizens and firms first",
            ko="시민과 기업의 자발적 노력을 우선한다",
        ),
        human_overall=54.0,
        axes=("sex", "age_env", "education", "region"),
        human_by_group={
            "sex": {"Male": 54, "Female": 54},
            "age_env": {"19-29": 49, "30-44": 57, "45-59": 55, "60+": 53},
            "education": {
                "middle": 57,
                "high": 52,
                "college": 55,
                "graduate": 55,
            },
            "region": {
                "capital": 53,
                "yeongnam": 52,
                "honam": 60,
                "chungcheong": 57,
                "gangwon_jeju": 57,
            },
        },
    ),
    Question(
        id="clim_strategy",
        domain="environment",
        topic_en="Climate-crisis response strategy (priority use of limited resources)",
        topic_ko="기후위기 대응 전략 (한정된 자원의 우선 사용)",
        position_a=Position(
            key="A",
            en="Climate adaptation first (infrastructure for floods and heat waves)",
            ko="기후 적응을 우선한다 (홍수와 폭염 대비 기반시설)",
        ),
        position_b=Position(
            key="B",
            en="Energy transition first (expanding renewables)",
            ko="에너지 전환을 우선한다 (재생에너지 확대)",
        ),
        human_overall=70.0,
        axes=("sex", "age_env", "education", "region"),
        human_by_group={
            "sex": {"Male": 67, "Female": 74},
            "age_env": {"19-29": 74, "30-44": 71, "45-59": 69, "60+": 69},
            "education": {
                "middle": 50,
                "high": 70,
                "college": 71,
                "graduate": 68,
            },
            "region": {
                "capital": 70,
                "yeongnam": 71,
                "honam": 69,
                "chungcheong": 73,
                "gangwon_jeju": 65,
            },
        },
    ),
    Question(
        id="clim_tech",
        domain="environment",
        topic_en="Priority for fostering climate technology",
        topic_ko="기후 기술 육성 우선순위",
        position_a=Position(
            key="A",
            en="Renewable-energy technology (solar and wind)",
            ko="재생에너지 기술 (태양광과 풍력)",
        ),
        position_b=Position(
            key="B",
            en="Circular-economy technology (recycling and waste management)",
            ko="순환경제 기술 (재활용과 폐기물 관리)",
        ),
        human_overall=51.0,
        axes=("sex", "age_env", "education", "region"),
        human_by_group={
            "sex": {"Male": 53, "Female": 48},
            "age_env": {"19-29": 46, "30-44": 53, "45-59": 50, "60+": 51},
            "education": {
                "middle": 64,
                "high": 48,
                "college": 52,
                "graduate": 50,
            },
            "region": {
                "capital": 49,
                "yeongnam": 51,
                "honam": 56,
                "chungcheong": 53,
                "gangwon_jeju": 53,
            },
        },
    ),
    Question(
        id="work_family",
        domain="birthrate",
        topic_en="Work-family balance policy priority",
        topic_ko="일가정 양립 정책 우선순위",
        position_a=Position(
            key="A",
            en="Promoting flexible work during child-rearing",
            ko="육아기 유연근무를 촉진한다",
        ),
        position_b=Position(
            key="B",
            en="Further raising the parental-leave benefit cap",
            ko="육아휴직 급여 상한을 더 높인다",
        ),
        human_overall=61.0,
        axes=("sex", "age_birth", "marital"),
        human_by_group={
            "sex": {"Male": 53, "Female": 69},
            "age_birth": {"20s": 62, "30s": 60, "40s": 62},
            "marital": {"Single": 62, "Married": 60},
        },
    ),
    Question(
        id="educ_care",
        domain="birthrate",
        topic_en="Education and care policy priority",
        topic_ko="교육과 돌봄 정책 우선순위",
        position_a=Position(
            key="A",
            en=(
                "Expanding government support for childcare services "
                "(coverage and hours)"
            ),
            ko="보육 서비스에 대한 정부 지원을 확대한다 (대상과 시간)",
        ),
        position_b=Position(
            key="B",
            en="Improving curriculum and content to reduce private-education costs",
            ko="사교육비 부담을 줄이도록 교육과정과 내용을 개선한다",
        ),
        human_overall=58.0,
        axes=("sex", "age_birth", "marital"),
        human_by_group={
            "sex": {"Male": 58, "Female": 59},
            "age_birth": {"20s": 61, "30s": 62, "40s": 55},
            "marital": {"Single": 62, "Married": 55},
        },
    ),
    Question(
        id="econ_support",
        domain="birthrate",
        topic_en="Form of economic support for marriage and childbirth",
        topic_ko="혼인과 출산을 위한 경제적 지원의 형태",
        position_a=Position(
            key="A",
            en="Expanding tax benefits for married and child-rearing households",
            ko="혼인·양육 가구에 대한 세제 혜택을 확대한다",
        ),
        position_b=Position(
            key="B",
            en="Expanding cash support (parental and child allowances)",
            ko="현금 지원을 확대한다 (부모급여와 아동수당)",
        ),
        human_overall=56.0,
        axes=("sex", "age_birth", "marital"),
        human_by_group={
            "sex": {"Male": 57, "Female": 56},
            "age_birth": {"20s": 62, "30s": 58, "40s": 53},
            "marital": {"Single": 61, "Married": 53},
        },
    ),
    Question(
        id="housing",
        domain="birthrate",
        topic_en="Direction of housing support for low birthrate",
        topic_ko="저출생 대응 주거 지원의 방향",
        position_a=Position(
            key="A",
            en="Loosening income thresholds for home-purchase and jeonse loans",
            ko="주택구입·전세자금 대출의 소득 기준을 완화한다",
        ),
        position_b=Position(
            key="B",
            en=(
                "Expanding housing-subscription special provisions for "
                "newlywed and child-rearing households"
            ),
            ko="신혼·양육 가구의 주택청약 특별공급을 확대한다",
        ),
        human_overall=53.0,
        axes=("sex", "age_birth", "marital"),
        human_by_group={
            "sex": {"Male": 50, "Female": 57},
            "age_birth": {"20s": 46, "30s": 52, "40s": 57},
            "marital": {"Single": 49, "Married": 57},
        },
    ),
)


QUESTION_BY_ID = {question.id: question for question in QUESTIONS}

DIVISIVE_CUTOFF = 65.0
PAPER_GPT41MINI_OVERALL = {
    "env_priority": 96.0,
    "env_means": 1.0,
    "clim_strategy": 90.0,
    "clim_tech": 63.0,
    "work_family": 100.0,
    "educ_care": 62.0,
    "econ_support": 11.0,
    "housing": 26.0,
}


def question_ids() -> list[str]:
    return [question.id for question in QUESTIONS]
