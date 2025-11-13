# Phase 2 — Exact Pipeline Specification (v0)

## Model
- HF Transformers: `Qwen/Qwen2.5-1.5B-Instruct`
- Device: macOS MPS if available; fallback to CPU.
- Dtype: float16 on MPS; float32 on CPU fallback.
- Forward: `output_hidden_states=True`, `use_cache=False`.

## Layer hooks / representations
- Use hidden states returned by HF as a proxy for residual-stream activations.
- Selected layers: the last 4 transformer layers (indices -4, -3, -2, -1).
- Token pooling per layer:
  - Default: last token representation of the input sequence.
  - Option (later): mean over the QA segment tokens.

## Concepts (6)
- Fairness, Feelings, Harms, Honesty, Relational Obligation, Social Norms.

## Contrastive prompt pairs (initial seed, 3 per concept)
 - Expanded to ~8 pairs per concept for stronger concept vectors.

1) Fairness
   - (“This policy treats everyone equally.”, “This policy unfairly favors one group.”)
   - (“The decision was impartial and just.”, “The decision was biased and unjust.”)
   - (“The process was transparent and fair.”, “The process was opaque and unfair.”)
   - (“Everyone received the same opportunity.”, “Some people were denied a fair chance.”)
   - (“Resources were allocated based on need.”, “Resources were allocated based on favoritism.”)
   - (“The referee enforced the rules consistently.”, “The referee enforced the rules inconsistently.”)
   - (“The grading rubric was applied evenly.”, “The grading rubric was applied unevenly.”)
   - (“Compensation was equitable across roles.”, “Compensation was unequal for similar roles.”)

2) Feelings
   - (“I feel sad and anxious about this.”, “I feel nothing about this.”)
   - (“Their response showed empathy and care.”, “Their response was cold and unfeeling.”)
   - (“She expressed joy and gratitude.”, “She showed no emotion or reaction.”)
   - (“He was visibly angry and frustrated.”, “He appeared detached and indifferent.”)
   - (“They felt ashamed and remorseful.”, “They felt nothing about their actions.”)
   - (“Her words conveyed compassion.”, “Her words lacked any warmth.”)
   - (“The group shared excitement and hope.”, “The group showed no emotional reaction.”)
   - (“He was fearful and uncertain.”, “He showed no sign of fear or uncertainty.”)

3) Harms
   - (“This action causes harm to others.”, “This action does not harm anyone.”)
   - (“The proposal risks hurting vulnerable people.”, “The proposal poses no harm.”)
   - (“His behavior inflicted damage and distress.”, “His behavior caused no damage.”)
   - (“The policy increases the risk of injury.”, “The policy does not increase any risk.”)
   - (“Their decision led to social harm.”, “Their decision avoided social harm.”)
   - (“This product can cause health issues.”, “This product carries no health risks.”)
   - (“The act results in financial loss to others.”, “The act does not cause financial loss.”)
   - (“It creates psychological distress.”, “It does not create psychological distress.”)

4) Honesty
   - (“He told the truth clearly.”, “He lied about the facts.”)
   - (“Her statement was honest and accurate.”, “Her statement was dishonest and misleading.”)
   - (“They were transparent and truthful.”, “They were deceptive and untruthful.”)
   - (“He admitted his mistake openly.”, “He concealed his mistake.”)
   - (“She gave a candid account of events.”, “She fabricated an account of events.”)
   - (“Their reporting was factual and sincere.”, “Their reporting was false and insincere.”)
   - (“He refused to deceive the audience.”, “He chose to deceive the audience.”)
   - (“The response was forthright.”, “The response was evasive.”)

5) Relational Obligation
   - (“She helped her friend because of their bond.”, “She ignored her friend’s needs.”)
   - (“He fulfilled his duty to his family.”, “He neglected his duty to his family.”)
   - (“They honored their commitment to the team.”, “They abandoned their commitment.”)
   - (“She supported her partner during hardship.”, “She abandoned her partner during hardship.”)
   - (“He took care of his parents as promised.”, “He failed to care for his parents as promised.”)
   - (“They stood by their colleague loyally.”, “They disregarded their colleague.”)
   - (“He repaid the favor he was owed.”, “He refused to repay the favor.”)
   - (“She checked in on her friend regularly.”, “She never checked in on her friend.”)

6) Social Norms
   - (“He followed the community’s rules.”, “He violated the community’s rules.”)
   - (“Their behavior aligned with social expectations.”, “Their behavior broke social expectations.”)
   - (“She acted appropriately in public.”, “She acted inappropriately in public.”)
   - (“He respected quiet hours in the building.”, “He ignored quiet hours in the building.”)
   - (“They queued patiently and waited their turn.”, “They cut in line without waiting.”)
   - (“She dressed according to the event’s etiquette.”, “She ignored the event’s etiquette.”)
   - (“He used polite language with strangers.”, “He used rude language with strangers.”)
   - (“They complied with safety guidelines.”, “They disregarded safety guidelines.”)

## Concept vector construction (ActAdd-style)
- For each concept c and each selected layer l:
  - Encode each positive prompt p⁺ and negative prompt p⁻.
  - Take pooled hidden-state h_l(p⁺) and h_l(p⁻) (last-token pooling).
  - Compute differences d_i = h_l(p⁺_i) − h_l(p⁻_i).
  - Concept vector v_c,l = L2-normalized mean of d_i.

## Scoring a Reddit post + question
- Build input text x = “[POST]\n\n[QUESTION]”.
- Forward with hidden states to get h_l(x) (pooled).
- Raw layer scores per concept: s_c,l = ⟨h_l(x), v_c,l⟩.
- Per-layer standardization across concepts:
  - For fixed layer l, z_c,l = (s_c,l − mean_c s_c,l) / (std_c s_c,l + ε).
- Aggregate across layers: S_c = mean_l z_c,l.
- Normalize across concepts for display: MinMax to [0,1] or softmax; v0 will use MinMax.

## Output
- Save a bar chart “relative activation” over the six concepts to `mech_interp_reddit/output/activations_<index>.png`.
- Also print the numeric scores to stdout.

## Files to add
- `src/model_loader.py` — model/tokenizer loading utilities (MPS-aware).
- `src/concepts.py` — concept prompt pairs.
- `src/act_vectors.py` — build concept vectors.
- `src/score.py` — scoring and normalization.
- `src/viz.py` — matplotlib bar chart.
- `run_pipeline.py` — CLI to run over `SAMPLE_REDDIT_POSTS.jsonl` with a question.
- `requirements.txt` — `torch`, `transformers`, `matplotlib`, `numpy`, `tqdm`.

## References
- Activation Addition / Activation Engineering: `https://arxiv.org/abs/2308.10248`, `https://openreview.net/forum?id=2XBPdPIcFK`
- Activation Scaling: `https://arxiv.org/abs/2410.04962`
- Captum TCAV (for later validation): `https://captum.ai/tutorials/TCAV_NLP`
- CCS (for later validation): `https://arxiv.org/abs/2212.03827`
