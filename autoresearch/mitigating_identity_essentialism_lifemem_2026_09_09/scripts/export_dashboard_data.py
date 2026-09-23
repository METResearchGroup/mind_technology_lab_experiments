from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lifemem.config import LifeMemConfig
from lifemem.experiment import run_suite, write_json
from lifemem.panel import build_panel, save_panel
from lifemem.retrieval import retrieve_events

DASHBOARD_DATA = ROOT / "dashboard" / "public" / "data"


def retrieval_playground(n_agents: int = 24, n_waves: int = 6) -> dict:
    panel = build_panel(n_agents=n_agents, n_waves=n_waves, events_per_wave=8, seed=42)
    config = LifeMemConfig()
    questions = [
        {
            "variable": q.variable,
            "question": q.question,
            "options": [o.text for o in q.options],
        }
        for q in panel.questions
    ]
    agents = []
    for agent in panel.agents:
        events = [
            event
            for wave in panel.waves
            for event in panel.events_by_wave[(agent.profile.agent_id, wave)]
        ]
        retrievals = []
        last = panel.waves[-1]
        for question in panel.questions:
            ranked = retrieve_events(
                question, events, last, config.top_k, config.forgetting_alpha
            )
            retrievals.append(
                {
                    "variable": question.variable,
                    "hits": [
                        {
                            "event_id": item.event.event_id,
                            "wave": item.event.wave,
                            "statement": item.event.statement,
                            "similarity": item.semantic_similarity,
                            "recency": item.recency_weight,
                            "score": item.final_score,
                        }
                        for item in ranked
                    ],
                }
            )
        agents.append(
            {
                "agent_id": agent.profile.agent_id,
                "sex": agent.profile.sex,
                "ses": agent.profile.ses,
                "education": agent.profile.education,
                "religion": agent.profile.religion,
                "region": agent.profile.region,
                "birth_year": agent.profile.birth_year,
                "occupation": agent.profile.occupation,
                "profile_text": agent.profile.profile_text,
                "events": [
                    {
                        "event_id": event.event_id,
                        "wave": event.wave,
                        "section": event.section,
                        "question": event.question,
                        "answer": event.answer_text,
                        "statement": event.statement,
                        "tags": list(event.tags),
                    }
                    for event in events
                ],
                "answers": [
                    {
                        "wave": wave,
                        "variable": question.variable,
                        "answer": panel.humans[
                            (agent.profile.agent_id, wave, question.variable)
                        ],
                    }
                    for wave in panel.waves
                    for question in panel.questions
                ],
                "retrievals": retrievals,
            }
        )
    return {"questions": questions, "waves": list(panel.waves), "agents": agents}


def main() -> None:
    DASHBOARD_DATA.mkdir(parents=True, exist_ok=True)
    panel = build_panel(n_agents=24, n_waves=6, events_per_wave=8, seed=42)
    save_panel(panel, ROOT / "data" / "synthetic_panel.json")
    results = run_suite(LifeMemConfig(), n_agents=24, n_waves=6, events_per_wave=8)
    paper = json.loads(
        (ROOT / "data" / "paper_results.json").read_text(encoding="utf-8")
    )
    compact_methods = {
        name: {
            "kl": row["kl"],
            "wg_gap": row["wg_gap"],
            "entropy_gap": row["entropy_gap"],
            "transition_js": row["transition_js"],
            "n_records": row["n_records"],
        }
        for name, row in results["methods"].items()
    }
    gpu = _gpu_payload()
    bundle = {
        "paper": paper,
        "replication": {
            **results,
            "methods": compact_methods,
        },
        "playground": retrieval_playground(),
        "takeaways": _takeaways(paper, compact_methods, results["identity"], gpu),
        "notes": {
            "restricted_data": (
                "Add Health and Understanding Society respondent files are not redistributable. "
                "This replication uses a synthetic six-wave panel with the paper's method, "
                "metrics, and hyperparameters. The default backbone is Qwen/Qwen3.5-4B."
            ),
            "encoder": (
                "CPU replication uses a deterministic hashed n-gram encoder. "
                "The paper uses all-MiniLM-L6-v2 for LifeMem and bge-m3 for Event RAG."
            ),
            "parametric_memory": (
                "CPU replication stores persistent QA bindings as a stand-in for per-agent LoRA. "
                "The Hugging Face Jobs path trains real PEFT adapters (rank 8, alpha 16, replay 4, "
                "two epochs per wave) on Qwen/Qwen3.5-4B."
            ),
            "decay": "Paper reports lambda=0.105; official configs set forgetting_alpha=0.9.",
            "gpu": (
                "GPU entry: scripts/submit_hf_job.py uploads sources and runs scripts/hf_job.py "
                "on a10g-small. Results land in data/gpu_results.json, the Hub dataset, and S3."
            ),
        },
        "gpu": gpu,
    }
    write_json(bundle, DASHBOARD_DATA / "results.json")
    write_json(results, ROOT / "data" / "replication_results.json")
    print(json.dumps(compact_methods, indent=2, default=str))


def _compact_methods(methods: dict) -> dict:
    return {
        name: {
            "kl": row["kl"],
            "wg_gap": row["wg_gap"],
            "entropy_gap": row["entropy_gap"],
            "transition_js": row["transition_js"],
            "n_records": row["n_records"],
        }
        for name, row in methods.items()
    }


def _gpu_payload() -> dict:
    results_path = ROOT / "data" / "gpu_results.json"
    status_path = ROOT / "data" / "gpu_job_status.json"
    if results_path.exists():
        data = json.loads(results_path.read_text(encoding="utf-8"))
        payload = {
            "status": "completed",
            "config": data.get("config", {}),
            "methods": _compact_methods(data.get("methods", {})),
            "identity": data.get("identity"),
            "device": data.get("device"),
            "hardware": data.get("hardware"),
            "lora": data.get("lora"),
            "model": data.get("backbone") or data.get("config", {}).get("model"),
            "n_agents": data.get("config", {}).get("n_agents"),
            "n_waves": data.get("config", {}).get("n_waves"),
        }
        if status_path.exists():
            status = json.loads(status_path.read_text(encoding="utf-8"))
            payload["url"] = status.get("url")
            payload["flavor"] = status.get("flavor")
            payload["src_repo"] = status.get("src_repo")
        return payload
    if status_path.exists():
        return json.loads(status_path.read_text(encoding="utf-8"))
    return {
        "status": "pending",
        "model": "Qwen/Qwen3.5-4B",
        "flavor": "a10g-small",
        "hint": (
            "Run scripts/submit_hf_job.py after adding Hugging Face Jobs credits. "
            "The runner trains per-agent LoRA on Qwen/Qwen3.5-4B."
        ),
    }


def _takeaways(
    paper: dict, methods: dict, identity: dict, gpu: dict | None = None
) -> list[dict]:
    llama = paper["table1"]["Llama-3.1-8B-Instruct"]
    rows = [
        {
            "id": "essentialism",
            "title": "Static profiles cluster by class",
            "body": (
                "On World Values Survey wave 7 (N=2,000), human SES groups overlap "
                f"(silhouette {paper['wvs_silhouette']['human']}), while Llama-8B agents "
                f"conditioned on the same labels separate ({paper['wvs_silhouette']['static_profile_llama8b']})."
            ),
            "stat": f"{paper['wvs_silhouette']['static_profile_llama8b']:.2f}",
            "stat_label": "profile silhouette vs −0.02 human",
        },
        {
            "id": "kl",
            "title": "LifeMem cuts KL on both surveys",
            "body": (
                "Llama-8B Add Health KL falls from 8.67 (Profile) and 5.83 (Event RAG) "
                f"to {llama['LifeMem']['ah_kl']}. Understanding Society KL falls to "
                f"{llama['LifeMem']['us_kl']}."
            ),
            "stat": f"{llama['LifeMem']['ah_kl']:.2f}",
            "stat_label": "Add Health KL, Llama-8B",
        },
        {
            "id": "ablation",
            "title": "Both memories are doing work",
            "body": (
                "Dropping parametric memory or structured retrieval raises KL on every backbone. "
                "Retrieval supplies question-specific evidence; LoRA keeps unretrieved experience."
            ),
            "stat": "2-of-2",
            "stat_label": "components required",
        },
        {
            "id": "replication",
            "title": "Same ranking on a synthetic panel",
            "body": (
                "With the paper's K=5, alpha=0.9, and metrics, LifeMem KL is "
                f"{methods['lifemem']['kl']:.3f} vs Profile {methods['profile']['kl']:.3f} "
                f"and Direct {methods['direct']['kl']:.3f} on 24 synthetic agents."
            ),
            "stat": f"{methods['lifemem']['kl']:.2f}",
            "stat_label": "replication KL (LifeMem)",
        },
        {
            "id": "identity",
            "title": "Profile agents still look essentialist",
            "body": (
                "Last-wave SES silhouette is "
                f"{identity['human']['silhouette']:.3f} for synthetic humans, "
                f"{identity['profile']['silhouette']:.3f} for Profile, and "
                f"{identity['lifemem']['silhouette']:.3f} for LifeMem."
            ),
            "stat": f"{identity['profile']['silhouette']:.2f}",
            "stat_label": "Profile SES silhouette",
        },
        {
            "id": "latency",
            "title": "Cheaper than Event RAG",
            "body": (
                "On Add Health, LifeMem averages 161.7 ms vs Event RAG 1094.2 ms. "
                "Full History is slower and still worse on KL."
            ),
            "stat": "6.8×",
            "stat_label": "Event RAG / LifeMem latency",
        },
    ]
    gpu_methods = (gpu or {}).get("methods") or {}
    if gpu and gpu.get("status") == "completed" and "lifemem" in gpu_methods:
        gpu_identity = gpu.get("identity") or {}
        profile_sil = (gpu_identity.get("profile") or {}).get("silhouette")
        lifemem_sil = (gpu_identity.get("lifemem") or {}).get("silhouette")
        best = min(gpu_methods, key=lambda name: gpu_methods[name]["kl"])
        body = (
            f"{gpu.get('model', 'Qwen/Qwen3.5-4B')} LoRA on "
            f"{gpu.get('device') or 'Hugging Face Jobs'}. "
            f"LifeMem KL {gpu_methods['lifemem']['kl']:.3f} vs Profile "
            f"{gpu_methods['profile']['kl']:.3f}; lowest KL is {best} "
            f"({gpu_methods[best]['kl']:.3f}). "
        )
        if profile_sil is not None and lifemem_sil is not None:
            body += (
                f"Last-wave SES silhouette drops from {profile_sil:.2f} (Profile) "
                f"to {lifemem_sil:.2f} (LifeMem)."
            )
        rows.append(
            {
                "id": "gpu",
                "title": "Qwen 4B on Hugging Face Jobs",
                "body": body,
                "stat": f"{gpu_methods['lifemem']['kl']:.2f}",
                "stat_label": "Qwen GPU LifeMem KL",
            }
        )
    return rows


if __name__ == "__main__":
    main()
