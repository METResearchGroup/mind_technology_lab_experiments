"""Synthetic chat and Reddit users used by the toy replica."""

from __future__ import annotations

from dataclasses import dataclass

from turing_rl.judge import StyleProfile, profile_text


@dataclass(frozen=True)
class Candidate:
    id: str
    label: str
    text: str
    kind: str


@dataclass(frozen=True)
class Example:
    example_id: str
    domain: str
    user_name: str
    persona: str
    history: tuple[str, ...]
    context: str
    ground_truth: str
    candidates: tuple[Candidate, ...]
    history_profile: StyleProfile


def _example(
    *,
    example_id: str,
    domain: str,
    user_name: str,
    persona: str,
    history: tuple[str, ...],
    context: str,
    ground_truth: str,
    candidates: tuple[Candidate, ...],
    quirks: tuple[str, ...],
) -> Example:
    joined_history = " ".join(history)
    return Example(
        example_id=example_id,
        domain=domain,
        user_name=user_name,
        persona=persona,
        history=history,
        context=context,
        ground_truth=ground_truth,
        candidates=candidates,
        history_profile=profile_text(joined_history, quirks),
    )


EXAMPLES: tuple[Example, ...] = (
    _example(
        example_id="chat_maya",
        domain="chat",
        user_name="Maya",
        persona=(
            "Short replies. Skeptical about hype. Uses contractions. Asks one "
            "pointed follow-up instead of listing options."
        ),
        history=(
            "nah that pitch felt off. who actually uses this day to day?",
            "keep it smaller. i don't want a 12 step plan.",
            "wait, did they even try it with real people?",
        ),
        context="Assistant: I can walk you through a comprehensive onboarding plan.",
        ground_truth="skip the plan. did anyone outside the team actually use it?",
        quirks=("nah", "wait", "keep it smaller"),
        candidates=(
            Candidate(
                "human_like",
                "Human-like follow-up",
                "skip the deck. wait, did anyone outside the team actually use it?",
                "human_like",
            ),
            Candidate(
                "assistant_like",
                "Assistant-like",
                (
                    "Great question! I'd be happy to help. Here are a few "
                    "comprehensive onboarding options you might consider, and "
                    "I can help you choose the right one."
                ),
                "assistant_like",
            ),
            Candidate(
                "content_match",
                "Content match, assistant tone",
                (
                    "Of course! The team should skip the plan, and I would be "
                    "happy to help check whether anyone outside the team used it."
                ),
                "content_match",
            ),
            Candidate(
                "generic",
                "Generic filler",
                "Okay sounds good, thanks for the information.",
                "generic",
            ),
            Candidate(
                "too_long",
                "Too long",
                (
                    "I think maybe we should perhaps generally speaking consider "
                    "whether the onboarding plan is too large, and then maybe "
                    "ask if real people used it, and also cover edge cases, "
                    "metrics, rollout, training, and next steps in detail."
                ),
                "too_long",
            ),
        ),
    ),
    _example(
        example_id="reddit_jordan",
        domain="reddit",
        user_name="Jordan",
        persona=(
            "Snarky Reddit commenter. Short punchlines. Uses slang. Does not "
            "hedge or write an essay."
        ),
        history=(
            "lol no. that's the whole post.",
            "bruh they buried the actual mistake in paragraph 4.",
            "wild that people still defend this.",
        ),
        context=(
            "OP: Am I overreacting for leaving after they rewrote my work "
            "without asking?"
        ),
        ground_truth=(
            "nah you're not overreacting. rewriting it and acting shocked is the tell."
        ),
        quirks=("lol", "bruh", "wild"),
        candidates=(
            Candidate(
                "human_like",
                "Human-like follow-up",
                "lol no. rewriting it then acting shocked is the tell.",
                "human_like",
            ),
            Candidate(
                "assistant_like",
                "Assistant-like",
                (
                    "I'm here to help. It might be worth considering both "
                    "perspectives. Here are some steps: 1. Pause. 2. Write a "
                    "calm message. 3. Let me know if you need more advice."
                ),
                "assistant_like",
            ),
            Candidate(
                "content_match",
                "Content match, assistant tone",
                (
                    "Certainly. You are not overreacting, and rewriting the work "
                    "then acting shocked is an important signal I can help you "
                    "unpack."
                ),
                "content_match",
            ),
            Candidate(
                "generic",
                "Generic filler",
                "This is a complicated situation and there are many factors.",
                "generic",
            ),
            Candidate(
                "too_short",
                "Too short",
                "yes",
                "too_short",
            ),
        ),
    ),
    _example(
        example_id="chat_priya",
        domain="chat",
        user_name="Priya",
        persona=(
            "Direct and practical. Talks in first person. Cuts off waffle. "
            "Cares about time cost."
        ),
        history=(
            "i've got 20 minutes, not a workshop.",
            "if it needs a new account i'm out.",
            "just tell me the one setting that actually changes the output.",
        ),
        context="Assistant: Would you like a complete tour of every advanced setting?",
        ground_truth="no tour. which one setting actually changes the output?",
        quirks=("i've got", "i'm out", "one setting"),
        candidates=(
            Candidate(
                "human_like",
                "Human-like follow-up",
                (
                    "no tour. i've got 20 minutes. which one setting "
                    "actually changes the output?"
                ),
                "human_like",
            ),
            Candidate(
                "assistant_like",
                "Assistant-like",
                (
                    "Great question! I'd be happy to give you a comprehensive "
                    "tour of every advanced setting, and I can help you compare "
                    "them in a structured list."
                ),
                "assistant_like",
            ),
            Candidate(
                "content_match",
                "Content match, assistant tone",
                (
                    "Of course! There should be no tour, and I can help you find "
                    "the one setting that actually changes the output."
                ),
                "content_match",
            ),
            Candidate(
                "generic",
                "Generic filler",
                "Sure, whatever you think is best.",
                "generic",
            ),
            Candidate(
                "too_long",
                "Too long",
                (
                    "Perhaps we could generally speaking walk through each "
                    "advanced setting, describe tradeoffs, show screenshots, "
                    "and then circle back to which control changes the output "
                    "after a full overview."
                ),
                "too_long",
            ),
        ),
    ),
)


def get_examples() -> tuple[Example, ...]:
    return EXAMPLES
