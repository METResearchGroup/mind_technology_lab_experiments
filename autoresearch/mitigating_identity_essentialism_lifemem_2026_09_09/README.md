# LifeMem replication (arXiv:2608.19621)

Replication of [Mitigating Identity Essentialism in LLM Agents with Longitudinal Life Trajectories](https://arxiv.org/abs/2608.19621) (Wang, Zhou, Du, Su, Cao, Pan, Ai, Wu, Zhang, Liu). Official code: [halsayxi/LifeMem](https://github.com/halsayxi/LifeMem).

The paper's claim: static demographic prompts make LLM survey agents essentialist — within-group answers collapse, SES clusters separate. LifeMem stores life events in a hippocampal retriever (top-K=5, α=0.9) and consolidates them into a per-agent LoRA adapter.

## What this folder runs

Add Health and Understanding Society public-use files are restricted. This folder does not ship respondent microdata.

It does ship:

1. The paper's published Table 1–3 and appendix sweeps (Tables 12, 13, 14, 15).
2. A synthetic six-wave panel (24 agents, 8 Likert items, 12 event types) with the same metrics: KL, within-group pairwise gap, entropy gap, transition JS, SES silhouette.
3. Method prompts for Direct, Profile, Anti-stereotype, Full History, Event RAG, Random Event, LifeMem, and the two ablations.
4. A hashed n-gram encoder in place of MiniLM / bge-m3, and a persistent event-binding vector in place of LoRA, so the CPU path stays deterministic.

The default GPU backbone for a full run is `Qwen/Qwen3.5-4B` (lab default). The paper used Llama-3.1-8B-Instruct, Ministral-3-8B-Instruct-2512, and Qwen3.5-9B.

## Run the CPU suite

From the repository root:

```bash
uv sync --all-packages --extra test
uv run pytest autoresearch/mitigating_identity_essentialism_lifemem_2026_09_09/tests -q
uv run python autoresearch/mitigating_identity_essentialism_lifemem_2026_09_09/scripts/export_dashboard_data.py
```

That writes `data/replication_results.json` and `dashboard/public/data/results.json`.

## Dashboard

```bash
cd autoresearch/mitigating_identity_essentialism_lifemem_2026_09_09/dashboard
npm install
npm run dev
```

The UI has the paper takeaways, Table 1 charts, identity PCA, the synthetic ranking, a compose-a-person control, retrieval scores, latency, and hyperparameter sweeps.

## GPU follow-up

`scripts/hf_job.py` is a Hugging Face Jobs entry that re-runs the suite (still on the synthetic panel) with the lab default model. It does not train 100 real LoRA adapters; that needs the restricted survey files and the official repo.
