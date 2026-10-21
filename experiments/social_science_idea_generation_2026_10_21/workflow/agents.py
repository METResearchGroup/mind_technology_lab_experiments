# ruff: noqa: E501
"""DeepAgents chat model and role-bound agents for this workflow.

Run from the repository root:

    PYTHONPATH=/workspace:/workspace/experiments/social_science_idea_generation_2026_10_21 \\
      uv run --project experiments/social_science_idea_generation_2026_10_21 \\
      python -c "from workflow.agents import build_chat_model, build_role_agent; print('ok')"
"""

from deepagents import (
    GeneralPurposeSubagentProfile,
    HarnessProfile,
    create_deep_agent,
    register_harness_profile,
)
from langchain_openai import ChatOpenAI
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel

from workflow.constants import MAX_OUTPUT_TOKENS, MODEL_ID, REASONING_EFFORT
from workflow.roles import RoleSpec

# deepagents 0.7.29: general_purpose_subagent is GeneralPurposeSubagentProfile;
# this release also exposes execute, so exclude it with the filesystem tools.
_EXCLUDED_HARNESS_TOOLS = frozenset(
    {
        "ls",
        "read_file",
        "write_file",
        "edit_file",
        "delete",
        "glob",
        "grep",
        "execute",
    }
)

register_harness_profile(
    f"openai:{MODEL_ID}",
    HarnessProfile(
        excluded_tools=_EXCLUDED_HARNESS_TOOLS,
        general_purpose_subagent=GeneralPurposeSubagentProfile(enabled=False),
    ),
)


def build_chat_model(api_key: str) -> ChatOpenAI:
    """Construct the shared OpenAI chat model for all roles.

    Parameters
    ----------
    api_key
        OpenAI API key.

    Returns
    -------
    ChatOpenAI
        Configured model instance (not invoked).
    """
    return ChatOpenAI(
        model=MODEL_ID,
        api_key=api_key,
        use_responses_api=True,
        reasoning={"effort": REASONING_EFFORT},
        max_tokens=MAX_OUTPUT_TOKENS,
    )


def build_role_agent(
    role: RoleSpec,
    response_model: type[BaseModel],
    chat_model: ChatOpenAI,
) -> CompiledStateGraph:
    """Build one role agent with structured output.

    Parameters
    ----------
    role
        Speaker persona and system prompt.
    response_model
        Pydantic schema for the agent response.
    chat_model
        Shared chat model from :func:`build_chat_model`.

    Returns
    -------
    CompiledStateGraph
        Compiled LangGraph agent.
    """
    return create_deep_agent(
        model=chat_model,
        tools=[],
        system_prompt=role.system_prompt,
        response_format=response_model,
    )
