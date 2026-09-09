export type Finding = { id: string; title: string; body: string };

export type GroupRow = {
  axis: string;
  group: string;
  persona_share: number | null;
  human_share: number;
  n: number;
};

export type PaperGroupRow = {
  axis: string;
  group: string;
  persona_share: number;
  human_share: number | null;
};

export type QuestionRow = {
  id: string;
  domain: string;
  topic_en: string;
  topic_ko: string;
  position_a_en: string;
  position_b_en: string;
  position_a_ko: string;
  position_b_ko: string;
  human_overall: number;
  paper_gpt41mini: number;
  paper_groups: PaperGroupRow[];
  persona_overall: number | null;
  divisive: boolean;
  mean_group_gap: number | null;
  groups: GroupRow[];
};

export type ControlRow = {
  condition: string;
  question_id: string;
  persona_share: number | null;
  human_overall: number;
  n: number;
};

export type LiveSampleRow = {
  question_id: string;
  n: number;
  persona_share: number | null;
  paper_gpt41mini: number;
  human_overall: number;
};

export type Turn = {
  round_index: number;
  speaker_id: string;
  speaker_name: string;
  text: string;
  visible_to: string[];
};

export type Agent = {
  id: string;
  name: string;
  sex: string | null;
  age: number | null;
  education: string | null;
  region: string | null;
  assigned_side: string;
  stances: Array<string | null>;
};

export type Room = {
  room_id: string;
  question_id: string;
  protocol: string;
  start_composition: string;
  a_counts: number[];
  movement: number | null;
  agents: Agent[];
  turns: Turn[];
};

export type DebateVsMono = {
  question_id: string;
  debate_final_a: number | null;
  monologue_final_a: number | null;
  difference: number | null;
  debate_movement: number | null;
  monologue_movement: number | null;
};

export type DashboardData = {
  paper: {
    id: string;
    title: string;
    url: string;
    alphaxiv: string;
    findings: Finding[];
    table3: Record<string, Record<string, number>>;
    table6: Array<Record<string, string | number>>;
    table7: Array<Record<string, string | number>>;
  };
  replication: {
    model: string;
    provider: string;
    n_personas: number;
    cells: number;
    per_cell: number;
    language: string;
    persona_source: string;
    n_survey_full: number;
    n_rooms: number;
    offline: boolean;
    note: string;
  };
  survey: {
    mean_group_gap: number | null;
    mean_overall_gap: number | null;
    direction_matches: number;
    direction_total: number;
    near_unanimous_groups: number;
    questions: QuestionRow[];
    controls: ControlRow[];
    live_qwen_sample: LiveSampleRow[];
  };
  deliberation: {
    debate_vs_monologue: DebateVsMono[];
    rooms: Room[];
  };
  takeaways: Finding[];
};
