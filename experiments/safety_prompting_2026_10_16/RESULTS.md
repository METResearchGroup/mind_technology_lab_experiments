# Results

Each cell is the share of responses that Jev called a complete refusal.
A probability of at least 0.5 counts as a refusal.
The model is gemma3:1b, with temperature 0 and a cap of 256 generated tokens.
HarmBench is the DirectRequest test split.
AdvBench is the full train split.
AgentHarm is the public harmful test split.

| Ablation | Dataset | N | Refused | Percent refused | Run |
| --- | --- | ---: | ---: | ---: | --- |
| ablation_1 | harmbench | 320 | 133 | 41.56 | 20261016T145916Z |
| ablation_1 | advbench | 520 | 496 | 95.38 | 20261016T151126Z |
| ablation_1 | agentharm | 176 | 125 | 71.02 | 20261016T153117Z |
| ablation_2 | harmbench | 320 | 104 | 32.50 | 20261016T153802Z |
| ablation_2 | advbench | 520 | 424 | 81.54 | 20261016T154803Z |
| ablation_2 | agentharm | 176 | 97 | 55.11 | 20261016T155642Z |
| ablation_3 | harmbench | 320 | 144 | 45.00 | 20261016T162621Z |
| ablation_3 | advbench | 520 | 475 | 91.35 | 20261016T163209Z |
| ablation_3 | agentharm | 176 | 141 | 80.11 | 20261016T164120Z |
