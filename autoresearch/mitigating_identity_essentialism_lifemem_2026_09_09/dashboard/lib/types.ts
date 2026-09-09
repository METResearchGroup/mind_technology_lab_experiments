export type MethodMetrics = {
  kl: number;
  wg_gap: number;
  entropy_gap: number;
  transition_js: number | null;
  n_records: number;
};

export type ScatterPoint = {
  agent_id: string;
  ses: string;
  wave?: number;
  x: number;
  y: number;
};

export type IdentityCloud = {
  silhouette: number;
  points: ScatterPoint[];
};

export type Takeaway = {
  id: string;
  title: string;
  body: string;
  stat: string;
  stat_label: string;
};

export type RetrievalHit = {
  event_id: string;
  wave: number;
  statement: string;
  similarity: number;
  recency: number;
  score: number;
};

export type PlaygroundAgent = {
  agent_id: string;
  sex: string;
  ses: string;
  education: string;
  religion: string;
  region: string;
  birth_year: number;
  occupation: string;
  profile_text: string;
  events: {
    event_id: string;
    wave: number;
    section: string;
    question: string;
    answer: string;
    statement: string;
    tags: string[];
  }[];
  answers: { wave: number; variable: string; answer: string }[];
  retrievals: { variable: string; hits: RetrievalHit[] }[];
};

export type DashboardData = {
  paper: {
    paper: {
      id: string;
      title: string;
      authors: string[];
      venues: string;
      code: string;
      arxiv: string;
    };
    wvs_silhouette: { human: number; static_profile_llama8b: number; n: number };
    latency_ms: Record<string, Record<string, number>>;
    table1: Record<string, Record<string, Record<string, number>>>;
    table2: Record<string, Record<string, Record<string, number>>>;
    table12_decay: { alpha: number; kl: number; wg: number; ent: number }[];
    table13_replay: { eta: number; kl: number; wg: number; ent: number }[];
    table15_rank: { rank: number; kl: number; wg: number; ent: number }[];
    table14_retriever: {
      method: string;
      retriever: string;
      ah_kl: number;
      us_kl: number;
    }[];
    hyperparams: Record<string, string | number | string[]>;
  };
  replication: {
    config: Record<string, string | number>;
    methods: Record<string, MethodMetrics>;
    identity: Record<string, IdentityCloud>;
    adapter_pca: { points: ScatterPoint[] };
    examples: {
      method: string;
      agent_id: string;
      wave: number;
      variable: string;
      question: string;
      human: string;
      model: string | null;
      retrieved_event_ids: string[];
      prompt: string;
    }[];
  };
  playground: {
    questions: { variable: string; question: string; options: string[] }[];
    waves: number[];
    agents: PlaygroundAgent[];
  };
  takeaways: Takeaway[];
  notes: Record<string, string>;
  gpu: {
    status: string;
    error?: string;
    hint?: string;
    id?: string;
    url?: string;
    flavor?: string;
    timeout?: string;
    src_repo?: string;
    n_agents?: number;
    n_waves?: number;
    model?: string;
    device?: string;
    hub_url?: string;
    config?: Record<string, string | number>;
    methods?: Record<string, MethodMetrics>;
    identity?: Record<string, IdentityCloud>;
  } | null;
};

export const METHOD_LABELS: Record<string, string> = {
  direct: "Direct",
  profile: "Profile",
  anti_stereotype: "Anti-stereotype",
  full_history: "Full history",
  event_rag: "Event RAG",
  random_event: "Random event",
  lifemem: "LifeMem",
  lifemem_no_param: "w/o parametric",
  lifemem_no_struct: "w/o structured",
};

export const PAPER_METHODS = [
  "Direct",
  "Profile",
  "Multilingual",
  "Anti-Stereotype",
  "SimVBG",
  "Full History",
  "Event RAG",
  "Random Event",
  "LifeMem",
] as const;

export const METRIC_KEYS = [
  { id: "kl", label: "KL divergence" },
  { id: "wg_gap", label: "Within-group gap" },
  { id: "entropy_gap", label: "Entropy gap" },
  { id: "transition_js", label: "Transition JS" },
] as const;

export const SES_COLORS: Record<string, string> = {
  low: "#d06a4f",
  middle: "#e2b657",
  high: "#7eafd4",
};
