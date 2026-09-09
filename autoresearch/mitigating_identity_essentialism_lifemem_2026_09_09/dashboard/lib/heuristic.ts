export const LIKERT = [
  "Strongly disagree",
  "Disagree",
  "Neither agree nor disagree",
  "Agree",
  "Strongly agree",
];

export const EVENT_BANK = [
  {
    code: "HLT",
    question: "How often have you had trouble sleeping?",
    deltas: { HLTH: -1, LIFESAT: -1 },
  },
  {
    code: "JOB",
    question: "Have you been promoted or given more responsibility at work?",
    deltas: { FINSTR: -1, LIFESAT: 1, POLINT: 1 },
  },
  {
    code: "UNEMP",
    question: "Have you been unemployed and looking for work?",
    deltas: { FINSTR: 1, LIFESAT: -1, TRUST: -1 },
  },
  {
    code: "SCHOOL",
    question: "Have you enrolled in or completed a new educational programme?",
    deltas: { NETUSE: 1, POLINT: 1, NEIGH: -1 },
  },
  {
    code: "MOVE",
    question: "Have you moved to a different city or region?",
    deltas: { NEIGH: -1, CIVIC: -1, NETUSE: 1 },
  },
  {
    code: "MARRY",
    question: "Have you gotten married or started living with a partner?",
    deltas: { LIFESAT: 1, CIVIC: 1, NEIGH: 1 },
  },
  {
    code: "CHILD",
    question: "Has a child been born or joined your household?",
    deltas: { FINSTR: 1, CIVIC: -1, LIFESAT: 1 },
  },
  {
    code: "ILL",
    question: "Has a close family member had a serious illness?",
    deltas: { HLTH: -1, TRUST: 1, CIVIC: 1 },
  },
  {
    code: "VOL",
    question: "Have you started volunteering or community work?",
    deltas: { CIVIC: 1, POLINT: 1, TRUST: 1 },
  },
  {
    code: "HARD",
    question: "Has your household had trouble paying bills?",
    deltas: { FINSTR: 1, LIFESAT: -1, HLTH: -1 },
  },
] as const;

export const QUESTIONS = [
  { variable: "POLINT", question: "You are interested in political affairs." },
  { variable: "TRUST", question: "Most people can be trusted." },
  { variable: "LIFESAT", question: "You are satisfied with your life as a whole." },
  { variable: "HLTH", question: "In general, your health is excellent." },
  { variable: "NEIGH", question: "You would like to stay in your current neighbourhood." },
  { variable: "NETUSE", question: "The internet is important in your daily life." },
  { variable: "CIVIC", question: "You take part in local groups or volunteering." },
  { variable: "FINSTR", question: "You have been under financial strain recently." },
] as const;

export const SES_MEANS: Record<string, number[]> = {
  low: [-0.7, -0.4, -0.5, -0.6, -0.2, -0.3, -0.4, 0.8],
  middle: [0.0, 0.1, 0.0, 0.1, 0.0, 0.2, 0.1, 0.0],
  high: [0.8, 0.5, 0.6, 0.5, 0.3, 0.4, 0.5, -0.7],
};

const EVAL_INDEX: Record<string, number> = {
  POLINT: 0,
  TRUST: 1,
  LIFESAT: 2,
  HLTH: 3,
  NEIGH: 4,
  NETUSE: 5,
  CIVIC: 6,
  FINSTR: 7,
};

function clip(value: number): number {
  return Math.max(1, Math.min(5, Math.round(value)));
}

function eventShift(
  event: { question: string; intensity: number },
  variable: string,
): number {
  const bank = EVENT_BANK.find((item) => item.question === event.question);
  if (!bank) return 0;
  const deltas = bank.deltas as Record<string, number>;
  const delta = deltas[variable] ?? 0;
  const sign = event.intensity >= 3 ? 1 : -1;
  return 0.22 * sign * delta;
}

export function answerAsText(code: number): string {
  return `${code} · ${LIKERT[code - 1]}`;
}

export function simulateAnswers(args: {
  ses: "low" | "middle" | "high";
  individual: number;
  events: { question: string; intensity: number }[];
  variable: string;
}): Record<string, string> {
  const qIdx = EVAL_INDEX[args.variable];
  const sesShift = SES_MEANS[args.ses][qIdx];
  const history = args.events.reduce(
    (sum, event) => sum + eventShift(event, args.variable),
    0,
  );
  const recent = args.events.slice(Math.floor(args.events.length / 2));
  const recentShift = recent.reduce(
    (sum, event) => sum + eventShift(event, args.variable),
    0,
  );
  const retrieved = args.events
    .slice()
    .sort((a, b) => {
      const da = Math.abs(eventShift(a, args.variable));
      const db = Math.abs(eventShift(b, args.variable));
      return db - da;
    })
    .slice(0, 5);
  const retrievedShift = retrieved.reduce(
    (sum, event) => sum + eventShift(event, args.variable),
    0,
  );

  const direct = 3;
  const profile = clip(3 + sesShift);
  const anti = clip(3 + 0.58 * sesShift);
  const eventRag = clip(3 + 0.28 * sesShift + retrievedShift);
  const fullHistory = clip(3 + 0.32 * sesShift + 0.62 * recentShift);
  const lifemem = clip(
    3 +
      0.12 * sesShift +
      0.55 * args.individual +
      history +
      0.18 * retrievedShift,
  );

  return {
    Direct: answerAsText(direct),
    Profile: answerAsText(profile),
    "Anti-stereotype": answerAsText(anti),
    "Event RAG": answerAsText(eventRag),
    "Full history": answerAsText(fullHistory),
    LifeMem: answerAsText(lifemem),
  };
}
