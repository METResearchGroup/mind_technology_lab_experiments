from __future__ import annotations

from lifemem.config import LifeMemConfig
from lifemem.experiment import run_method, run_suite
from lifemem.panel import build_panel
from lifemem.parse import parse_option_code, strip_thinking
from lifemem.types import AgentState, RetrievedEvent, SurveyQuestion


def test_strip_thinking_and_parse() -> None:
    raw = "<think>I am considering class stereotypes</think>\nAnswer: 4"
    assert strip_thinking(raw).endswith("4")
    assert parse_option_code(raw, ("1", "2", "3", "4", "5")) == "4"


class ScriptedRespondent:
    def __init__(self) -> None:
        self.trained: list[tuple[str, str, int]] = []

    def train_adapter(self, method: str, agent: AgentState, events, replay) -> None:
        self.trained.append((method, agent.profile.agent_id, len(events)))

    def generate(
        self,
        prompt: str,
        question: SurveyQuestion,
        agent: AgentState,
        retrieved: list[RetrievedEvent],
        use_parametric: bool,
        method: str = "",
    ) -> str:
        del retrieved
        if "Answer with exactly one option number" not in prompt:
            raise AssertionError("survey option block missing")
        if use_parametric:
            return f"<think>{method} {agent.profile.agent_id}</think>\n2"
        if "Demographic profile:" in prompt:
            return "The option is 4."
        return "3"


def test_run_method_uses_injected_respondent() -> None:
    panel = build_panel(n_agents=2, n_waves=2, events_per_wave=2, seed=7)
    respondent = ScriptedRespondent()
    records = run_method(
        "lifemem",
        panel,
        LifeMemConfig(methods=("lifemem",), seed=7),
        respondent=respondent,
    )
    assert records
    assert all(row.parsed_answer == "2" for row in records)
    assert respondent.trained
    assert all(row[0] == "lifemem" for row in respondent.trained)


def test_scripted_suite_keeps_method_set() -> None:
    results = run_suite(
        LifeMemConfig(seed=7, methods=("direct", "profile")),
        n_agents=4,
        n_waves=2,
        events_per_wave=2,
        respondent=ScriptedRespondent(),
        backend="llm",
    )
    assert set(results["methods"]) == {"direct", "profile"}
    assert results["config"]["backend"] == "llm"
    assert results["methods"]["direct"]["n_records"] == 4 * 2 * 8
