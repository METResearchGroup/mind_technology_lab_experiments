export type Setting =
  | "base"
  | "profile_only"
  | "retrieval_only"
  | "profile_retrieval";

export type RiskType =
  | "irrelevant_personalization"
  | "preference_narrowing"
  | "sycophantic_bias";

export type SettingScores = {
  base: number;
  profile_only: number;
  retrieval_only: number;
  profile_retrieval: number;
  avg: number;
};

export type PaperRow = {
  model: string;
  irp: SettingScores;
  uir: SettingScores;
  syco: SettingScores;
};

export type BenchmarkRow = {
  model: string;
  gsm8k_base: number;
  gsm8k_profile: number;
  csqa_base: number;
  csqa_profile: number;
  mmlu_base: number;
  mmlu_profile: number;
};

export type AggregateRow = {
  risk_type: RiskType;
  setting: Setting;
  n: number;
  irp_resistance_pct: number | null;
  uir_pct: number | null;
  syco_resistance_pct: number | null;
  pis_noninduced_pct: number | null;
};

export type PlaygroundItem = {
  record_id: string;
  risk_type: RiskType;
  domain: string;
  question: string;
  persona: string;
  persona_id: string;
  attributes: Record<string, string | undefined>;
  setting: Setting;
  prompt: string;
  response: string;
  irp_score: number | null;
  irp_resistance_pct: number | null;
  uir_pct: number | null;
  coverage_rate: number | null;
  relative_coverage: number | null;
  syco_score: number | null;
  syco_resistance_pct: number | null;
  pis_score: number | null;
  flags: string[];
  covered_answers: string[];
  universal_answers: string[];
  useful_answers: string[];
  router_decision: string | null;
  retrieved_memories?: string[];
  user_is_at_fault?: boolean;
  stated_preference?: string | null;
  preferences?: string[];
};

export type ReplicationData = {
  generated_at_utc: string;
  backend: string;
  model_name: string;
  notes: string[];
  n_cases: number;
  n_generations: number;
  aggregate: { rows: AggregateRow[] };
  paper_table_2: PaperRow[];
  paper_mean_drops: {
    irp_drop_pct: number;
    uir_drop_pct: number;
    syco_drop_pct: number;
    n_models: number;
  };
  paper_benchmark_accuracy?: BenchmarkRow[];
  takeaways: string[];
  playground: PlaygroundItem[];
};

export const SETTINGS: Setting[] = [
  "base",
  "profile_only",
  "retrieval_only",
  "profile_retrieval",
];

export const SETTING_LABEL: Record<Setting, string> = {
  base: "Base",
  profile_only: "Profile",
  retrieval_only: "Memory",
  profile_retrieval: "Both",
};

export const RISK_LABEL: Record<RiskType, string> = {
  irrelevant_personalization: "Irrelevant personalization",
  preference_narrowing: "Preference narrowing",
  sycophantic_bias: "Sycophantic bias",
};
