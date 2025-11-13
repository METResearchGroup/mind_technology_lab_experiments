# Brain Dump — Concept Activations for Reddit Posts (Mechanistic Interpretability)

Objective: Given a Reddit post and a question, compute relative “activation strength” for six concepts — Fairness, Feelings, Harms, Honesty, Relational Obligation, Social Norms — during the model’s forward pass, and visualize as a bar chart. Use practical, light-weight mechanistic-interpretability methods that can run locally on a Mac with an open-source model (Qwen family).

## High-level approaches considered

1) Persona/Concept Vectors via Activation Engineering (a.k.a. steering vectors)
   - Core idea: derive a direction in activation space for a target concept from contrastive prompt pairs and then measure a sample’s projection onto that direction during inference.
   - Strong fit for our use-case because:
     - Lightweight and does not require fine-tuning.
     - Produces a scalar for “how much” a concept direction is present, per layer.
     - Can be built from small hand-crafted contrast sets for each concept.
   - Key references:
     - Activation Addition: Steering Language Models Without Optimization (Turner et al., 2023) — concept directions from prompt-pair contrasts. `https://arxiv.org/abs/2308.10248`
     - Steering LMs with Activation Engineering (OpenReview page) `https://openreview.net/forum?id=2XBPdPIcFK`
     - Persona vectors (Anthropic-style) for monitoring/controlling traits (discussion and reports) — Anthropic research article and community discussion links: `https://www.anthropic.com/research/persona-vectors` (linked via HN discussion: `https://news.ycombinator.com/item?id=44777760`) and arXiv preprint `https://arxiv.org/abs/2507.21509`
     - Activation Scaling for Steering and Interpreting LMs (Stoehr et al., 2024) — scaling/normalization choices. `https://arxiv.org/abs/2410.04962`

   Concrete sketch (based on Activation Addition [Turner et al., 2023] and activation scaling [Stoehr et al., 2024]):
   ```
   # Build concept vector per layer from prompt pairs
   for layer in L:
       vecs = []
       for (p_pos, p_neg) in concept_pairs:
           h_pos = hidden(layer, tokenize(p_pos))
           h_neg = hidden(layer, tokenize(p_neg))
           vecs.append(h_pos - h_neg)
       v_c[layer] = normalize(mean(vecs))

   # Score an input
   scores_per_layer = []
   for layer in L:
       h_x = hidden(layer, tokenize(x))
       s = dot(h_x, v_c[layer])
       scores_per_layer.append(s)

   # Standardize per layer and aggregate
   s_c = mean(zscore_across_concepts(scores_per_layer))
   ```
   - Implementation tips:
     - Use Hugging Face `output_hidden_states=True` to get per-layer hidden states (residual stream proxy).
     - Pooling: end-of-sequence token hidden state for causal LM; optionally mean-pool over QA segment tokens.
     - Stabilization: L2-normalize concept vectors; per-layer z-score across concepts before aggregation.

2) TCAV/GCAV-style Concept Activation Vectors (probing)
   - Train a linear probe to separate positive vs negative exemplars at a chosen layer; the normal vector is the “concept direction”; then use directional derivatives or dot products to score.
   - Pros: mature framework; straightforward; Captum for PyTorch has examples for NLP TCAV.
   - Cons: Requires labeled concept exemplars; probe misalignment and spurious-feature risks.
   - Key references:
     - Captum TCAV tutorial (NLP) `https://captum.ai/tutorials/TCAV_NLP`
     - GCAV — Controlling LLMs Through Concept Activation Vectors (H. Zhang et al., 2025) `https://arxiv.org/abs/2501.05764`
     - On probe reliability/misalignment: Probing the Probes (2025) `https://arxiv.org/abs/2511.04312`

   Concrete snippet (Captum TCAV-style workflow, adapted for text; see Captum tutorial):
   ```
   # 1) Collect activations for concept and random sets
   A_concept = [hidden(layer, x) for x in concept_texts]
   A_random  = [hidden(layer, x) for x in random_texts]

   # 2) Train linear classifier to separate concept vs random
   X = stack(A_concept + A_random)     # [n, d]
   y = [1]*len(A_concept) + [0]*len(A_random)
   w, b = train_linear_svm_or_logreg(X, y)

   # 3) CAV is the normal vector
   cav = normalize(w)

   # 4) TCAV score for input x via directional derivative:
   s = dot(grad_y_with_respect_to_h(layer, x), cav)
   ```
   Notes:
   - For GCAV (Zhang et al., 2025), steering can be done by subtracting a toxicity (or target) concept vector at chosen layers without fine-tuning, analogous to ActAdd.
   - Probe pitfalls: high probe accuracy ≠ aligned concept; use alignment metrics and sanity checks (Lysnæs-Larsen et al., 2025).

3) CCS (Contrast-Consistent Search) directions (unsupervised/weakly supervised)
   - Find a direction that satisfies logical/contrast constraints (e.g., “X is fair” vs “X is unfair”) using only model activations; can reduce prompt sensitivity and extract latent knowledge directions.
   - Pros: Less reliance on labels; can discover robust contrastive directions.
   - Cons: More complex to implement than ActAdd; tooling exists but is less “plug-and-play”.
   - Key references:
     - Discovering Latent Knowledge Without Supervision (Burns et al., 2022) `https://arxiv.org/abs/2212.03827`
     - CCS-Lib JOSS (2025) `https://joss.theoj.org/papers/10.21105/joss.06511`

   Concrete sketch (Burns et al., 2022):
   ```
   # Build contrast pairs: (statement, negation(statement))
   reps_pos = [hidden(layer, s) for s in S]
   reps_neg = [hidden(layer, not_s) for not_s in S_neg]

   # Find direction v that maps pos to +1 and neg to -1 with consistency constraints
   # Solve min_v  sum_i loss(sign(dot(h_i_pos, v))=+1) + loss(sign(dot(h_i_neg, v))=-1)
   # subject to logical consistency (pairs have opposite sign).
   v = optimize_contrast_consistency(reps_pos, reps_neg)
   v = normalize(v)

   score(x) = dot(hidden(layer, x), v)
   ```
   Notes:
   - CCS-Lib provides practical implementations (original CCS and enhanced variants) and batching/multi-GPU.

4) Sparse Autoencoders (SAEs) / Dictionary Learning
   - Decompose residual-stream activations into sparse, interpretable features; then map features to human concepts and measure activations of those features for inputs.
   - Pros: Rich feature-level interpretability; direct monitors for concept features.
   - Cons: Requires trained SAEs per model/layer; availability for Qwen may be limited; heavier lift.
   - Key references:
     - Anthropic: “Towards Monosemanticity” dictionary learning (2023) `https://transformer-circuits.pub/2023/monosemantic-features/`
     - SAELens (library) `https://pypi.org/project/sae-lens/`
     - Replication and commentary (Neel Nanda) `https://www.alignmentforum.org/posts/fKuugaxt2XLTkASkk/open-source-replication-and-commentary-on-anthropic-s`

   Concrete snippet (SAELens-style usage sketch):
   ```
   # Assume we have trained SAE for layer l: W_enc, W_dec, bias
   h = hidden(layer, x)                 # [d]
   z = relu(W_enc @ h + b)              # sparse codes
   h_recon = W_dec @ z                  # reconstruction

   # Concept mapping: pick SAE features F_c associated with a concept (via feature viz/labels)
   score_c = sum(z[j] for j in F_c)     # aggregate activation of concept-related features
   ```
   Notes:
   - Requires feature identification pipeline; powerful but more setup than ActAdd/TCAV for v0.

## Practical design choice for v0

We will start with Persona/Concept Vectors via Activation Engineering (ActAdd-style) because:
- Minimal data requirements: we can handcraft a small set of contrastive prompts for each concept.
- Fast iteration: compute a mean difference vector across a few pairs and get a usable concept direction.
- Clean scalar: projection ⟨h_l(x), v_concept⟩ (optionally standardized per layer) gives per-layer scores.
- Extensible: we can later validate/triangulate with TCAV or CCS for robustness.

We will add guardrails from literature (normalization/standardization, layer selection, calibration baselines) to reduce spurious artifacts.

## Proposed scoring method (per concept)

Notation:
- Let h_l(x) be the residual-stream activation at layer l for input x (token- or sequence-pooled; we’ll start with final-token pooled and also try mean over tokens in the question-answer segment).
- Build a concept direction v_c at layer l from k prompt pairs {(p_i^+, p_i^-)}:
  v_c,l := mean_i [ h_l(p_i^+) − h_l(p_i^−) ], then L2-normalize: v̂_c,l = v_c,l / ||v_c,l||.
- For a Reddit post + question input x, score:
  s_c,l(x) := ⟨ h_l(x), v̂_c,l ⟩.
- Aggregate across a layer set L (e.g., middle and late layers): s_c(x) := mean_{l∈L} z_l( s_c,l(x) ), where z_l is a per-layer standardization over all concepts to mitigate layer scale differences.
- Finally normalize across concepts for the bar chart: softmax/MinMax/Z-score across the six concepts to obtain relative activation.

Notes:
- We can try both “residual stream post-attention/pre-MLP” and “post-MLP” hooks; literature often targets residual stream to stay model-agnostic.
- We may include Activation Scaling ideas for robustness in intervention/measurement.

## Concept operationalization (vocab/examples)

We need small, clear contrast sets per concept (positive vs negative). We’ll craft 5–10 short prompt pairs each (statements or QA snippets) that strongly embody:
- Fairness vs Unfairness
- Feelings vs Emotional-void/Unfeeling
- Harms vs No-harm/Benefit
- Honesty vs Dishonesty
- Relational Obligation vs No/ignored obligation
- Social Norms vs Norm violations

Each pair should be plain-language and model-size appropriate (Qwen-1.5B–7B). We can later augment with synthetic pairs and sanity checks (swap labels, paraphrases).

For extra rigor, we can cross-check with:
- TCAV-style probes trained on the same layer activations (Captum) — as a validation signal.
- CCS-style directions from “X is [label]” vs negations — as a second extraction path.
- If any tension arises, flag for review; we prioritize ActAdd-direction scores for v0 and keep probes as diagnostics given “Probing the Probes” caveats.

## Model + local feasibility (Mac)

We need internal activations (by layer) to construct v_c and to score h_l(x). Therefore:
- Prefer Hugging Face Transformers with PyTorch (MPS) for Qwen small variants to register forward hooks easily.
- Candidate models on macOS:
  - Qwen2.5-0.5B / 1.5B / 3B Instruct (HF Transformers) — likely to fit on M-series with fp16/bfloat16; disable gradients.
  - If memory tight, try low-rank/quantized weights supported by HF (e.g., AWQ/GPTQ variants that still work with PyTorch) — but ensure activations remain accessible tensors.
- llama.cpp/GGUF is great for inference, but exposing all per-layer residual activations is nontrivial; for this project we should use HF for easy hooks.

References for local Qwen:
- Qwen running via llama.cpp (docs) `https://qwen.readthedocs.io/en/v2.5/run_locally/llama.cpp/` and latest docs `https://qwen.readthedocs.io/en/latest/run_locally/llama.cpp/`
- GGUF/llamafile variants exist (e.g., Qwen2.5-7B-Instruct GGUF) but again, internal hooks are the blocker for v0 (HF is better here).
- llama-cpp-python bindings (for completeness): `https://github.com/abetlen/llama-cpp-python`

Concrete snippet (HF, hidden states on MPS):
```
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

name = "Qwen/Qwen2.5-1.5B-Instruct"
tokenizer = AutoTokenizer.from_pretrained(name, use_fast=True)
model = AutoModelForCausalLM.from_pretrained(
    name, torch_dtype=torch.float16, device_map=None
)
device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
model.to(device)

text = "Example input"
inputs = tokenizer(text, return_tensors="pt").to(device)
with torch.no_grad():
    out = model(**inputs, output_hidden_states=True, use_cache=False)
# out.hidden_states: tuple(layer0,...,layerN) each [batch, seq, dim]
```

## Pipeline sketch (v0)

1) Load Qwen small HF model + tokenizer on MPS with torch.no_grad().
2) Register forward hooks to capture residual-stream activations at a configurable list of layers.
3) Build concept vectors:
   - For each concept c and each prompt pair (p^+, p^-), run forward passes and collect h_l.
   - Compute v̂_c,l = L2-normalized mean difference per layer; store per-layer directions.
4) Score a given Reddit post + question:
   - Tokenize concatenated context (post) and question; run model and capture h_l(x).
   - Compute s_c,l(x) = ⟨h_l(x), v̂_c,l⟩; aggregate across chosen layers with per-layer standardization.
   - Normalize across the six concepts to get relative scores.
5) Visualization: produce a bar chart (matplotlib) of relative activations for the six concepts.

Validation add-ons (iterative):
- Sanity checks: label swaps, paraphrases, negations.
- Cross-validate with TCAV (Captum) on a small synthetic set; record correlations with ActAdd scores.
- Optional CCS directions for selected concepts to compare against ActAdd vectors.

## Risks and mitigations

- Probe misalignment / spurious features (for TCAV/GCAV): use as validation signals, not primary measure; keep concept pairs diverse; add paraphrase/negation checks. (Ref: “Probing the Probes” `https://arxiv.org/abs/2511.04312`)
- Layer choice sensitivity: average across a handful of middle/late layers; consider per-layer z-scoring or activation scaling (Ref: Activation Scaling `https://arxiv.org/abs/2410.04962`).
- Token pooling choice: compare end-of-sequence vs mean over QA tokens; document choice.
- Concept drift/definition ambiguity: keep explicit definitions/examples per concept; iterate with user feedback.

## Datasets/benchmarks for future evaluation (optional)

- Moral reasoning probes/benchmarks and surveys for alignment checks and construct validity (e.g., EMNLP’25 “Staircase of Ethics”, fairness surveys, etc.). These are not required for v0 but useful for validation and stress testing.
  - Staircase of Ethics (EMNLP 2025) `https://aclanthology.org/2025.emnlp-main.806.pdf`
  - Bias/Fairness survey (Computational Linguistics 2024) `https://direct.mit.edu/coli/article/50/3/1097/121`

## Citations (selected)

- Activation Addition / Activation Engineering:
  - Turner et al., 2023: “Activation Addition: Steering Language Models Without Optimization” `https://arxiv.org/abs/2308.10248`
  - OpenReview page: “Steering Language Models with Activation Engineering” `https://openreview.net/forum?id=2XBPdPIcFK`
  - Activation Scaling: Stoehr et al., 2024 `https://arxiv.org/abs/2410.04962`
  - Persona vectors (Anthropic; commentary and arXiv): HN thread `https://news.ycombinator.com/item?id=44777760`, arXiv `https://arxiv.org/abs/2507.21509`

- TCAV / GCAV:
  - Captum TCAV (NLP tutorial) `https://captum.ai/tutorials/TCAV_NLP`
  - GCAV: “Controlling LLMs Through Concept Activation Vectors” (2025) `https://arxiv.org/abs/2501.05764`
  - Probe reliability: “Probing the Probes” (2025) `https://arxiv.org/abs/2511.04312`

- CCS / Latent knowledge:
  - Burns et al., 2022: “Discovering Latent Knowledge in LMs Without Supervision” `https://arxiv.org/abs/2212.03827`
  - CCS-Lib (JOSS 2025) `https://joss.theoj.org/papers/10.21105/joss.06511`

- SAEs / Dictionary learning:
  - Anthropic: “Towards Monosemanticity” `https://transformer-circuits.pub/2023/monosemantic-features/`
  - SAELens: `https://pypi.org/project/sae-lens/`
  - Neel Nanda replication/commentary `https://www.alignmentforum.org/posts/fKuugaxt2XLTkASkk/open-source-replication-and-commentary-on-anthropic-s`

- Qwen local usage:
  - Qwen + llama.cpp docs `https://qwen.readthedocs.io/en/v2.5/run_locally/llama.cpp/`
  - llama-cpp-python `https://github.com/abetlen/llama-cpp-python`

## Recommendation for v0 implementation

- Model: HF Transformers Qwen2.5 small (0.5B–1.5B) on macOS MPS for easy activation hooks.
- Method: ActAdd-style concept directions built from small, hand-crafted contrast sets per concept.
- Scoring: per-layer dot products with per-layer z-scaling, then aggregate; final across-concept normalization for bar chart.
- Validation: add TCAV probes and (optionally) CCS directions later to triangulate robustness.

If approved, next step is to lock the exact Qwen size (e.g., 1.5B), pick 4–6 layers to hook (mid/late), and draft the minimal code scaffold (hooks, concept vector builder, scorer, matplotlib chart).
