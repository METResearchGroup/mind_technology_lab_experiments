import json
from typing import Dict, Any, List
from time import perf_counter
from opik import track
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from app.evals.opik_metrics import score_with_opik_metrics
from app.simulation import LIKE_DECISION_PROMPT, POST_DRAFTING_PROMPT

EVAL_CASES: List[Dict[str, Any]] = [
    {
        "eval_name": "v1_persona_alignment",
        "case_id": "case_001",
        "agent_handle": "alice",
        "bio_str": '{"summary": {"interests": ["tech", "ai"]}, "politics_and_values": {"values":["innovation"]}}',
        "feed_with_uris": [{"uri": "at://sim/x/1", "author": "bob", "text": "New AI model for summarization"}],
        "past_posts": [],
    },
]


@track
def run_eval_case(case: Dict[str, Any]) -> Dict[str, Any]:
    llm = ChatOpenAI(model="gpt-4o", temperature=0.7)
    session_id = case.get("session_id", "eval_suite")
    like_chain = ChatPromptTemplate.from_template(LIKE_DECISION_PROMPT) | llm.bind(
        response_format={"type": "json_object"}
    )
    draft_chain = ChatPromptTemplate.from_template(POST_DRAFTING_PROMPT) | llm.bind(
        response_format={"type": "json_object"}
    )

    feed_str = json.dumps(case["feed_with_uris"], indent=2)

    like_inputs = {"name": case["agent_handle"], "bio": case["bio_str"], "feed_posts": feed_str}
    t0 = perf_counter()
    like_result = like_chain.invoke(like_inputs)
    like_latency_s = perf_counter() - t0
    like_tokens = getattr(like_result, "response_metadata", {}).get("token_usage", {})

    draft_inputs = {
        "name": case["agent_handle"],
        "bio": case["bio_str"],
        "past_posts": json.dumps(case.get("past_posts", []), indent=2),
        "feed_posts": feed_str,
    }
    t1 = perf_counter()
    draft_result = draft_chain.invoke(draft_inputs)
    draft_latency_s = perf_counter() - t1
    draft_tokens = getattr(draft_result, "response_metadata", {}).get("token_usage", {})

    likes_data = json.loads(like_result.content)
    drafts_data = json.loads(draft_result.content)

    metrics_output = score_with_opik_metrics(
        agent_handle=case["agent_handle"],
        turn=-1,
        like_prompt=LIKE_DECISION_PROMPT.format(
            name=case["agent_handle"], bio=case["bio_str"], feed_posts=feed_str
        ),
        like_response=like_result.content,
        draft_prompt=POST_DRAFTING_PROMPT.format(
            name=case["agent_handle"],
            bio=case["bio_str"],
            past_posts=json.dumps(case.get("past_posts", []), indent=2),
            feed_posts=feed_str,
        ),
        draft_response=draft_result.content,
        session_id=session_id,
    )

    return {
        "eval_name": case["eval_name"],
        "case_id": case["case_id"],
        "metrics": metrics_output,
    }


@track
def run_eval_suite() -> Dict[str, Any]:
    results = [run_eval_case(c) for c in EVAL_CASES]
    return {"count": len(results), "results": results}


