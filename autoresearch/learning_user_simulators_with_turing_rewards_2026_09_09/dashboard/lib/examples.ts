import { profileText, type StyleProfile } from "@/lib/turing-math"

export type Candidate = {
  id: string
  label: string
  text: string
  kind: string
}

export type Example = {
  exampleId: string
  domain: "chat" | "reddit"
  userName: string
  persona: string
  history: string[]
  context: string
  groundTruth: string
  quirks: string[]
  candidates: Candidate[]
  historyProfile: StyleProfile
}

function makeExample(
  example: Omit<Example, "historyProfile">
): Example {
  return {
    ...example,
    historyProfile: profileText(example.history.join(" "), example.quirks),
  }
}

export const EXAMPLES: Example[] = [
  makeExample({
    exampleId: "chat_maya",
    domain: "chat",
    userName: "Maya",
    persona:
      "Short replies. Skeptical about hype. Uses contractions. Asks one pointed follow-up instead of listing options.",
    history: [
      "nah that pitch felt off. who actually uses this day to day?",
      "keep it smaller. i don't want a 12 step plan.",
      "wait, did they even try it with real people?",
    ],
    context: "Assistant: I can walk you through a comprehensive onboarding plan.",
    groundTruth: "skip the plan. did anyone outside the team actually use it?",
    quirks: ["nah", "wait", "keep it smaller"],
    candidates: [
      {
        id: "human_like",
        label: "Human-like follow-up",
        text: "skip the deck. wait, did anyone outside the team actually use it?",
        kind: "human_like",
      },
      {
        id: "assistant_like",
        label: "Assistant-like",
        text: "Great question! I'd be happy to help. Here are a few comprehensive onboarding options you might consider, and I can help you choose the right one.",
        kind: "assistant_like",
      },
      {
        id: "content_match",
        label: "Content match, assistant tone",
        text: "Of course! The team should skip the plan, and I would be happy to help check whether anyone outside the team used it.",
        kind: "content_match",
      },
      {
        id: "generic",
        label: "Generic filler",
        text: "Okay sounds good, thanks for the information.",
        kind: "generic",
      },
      {
        id: "too_long",
        label: "Too long",
        text: "I think maybe we should perhaps generally speaking consider whether the onboarding plan is too large, and then maybe ask if real people used it, and also cover edge cases, metrics, rollout, training, and next steps in detail.",
        kind: "too_long",
      },
    ],
  }),
  makeExample({
    exampleId: "reddit_jordan",
    domain: "reddit",
    userName: "Jordan",
    persona:
      "Snarky Reddit commenter. Short punchlines. Uses slang. Does not hedge or write an essay.",
    history: [
      "lol no. that's the whole post.",
      "bruh they buried the actual mistake in paragraph 4.",
      "wild that people still defend this.",
    ],
    context:
      "OP: Am I overreacting for leaving after they rewrote my work without asking?",
    groundTruth:
      "nah you're not overreacting. rewriting it and acting shocked is the tell.",
    quirks: ["lol", "bruh", "wild"],
    candidates: [
      {
        id: "human_like",
        label: "Human-like follow-up",
        text: "lol no. rewriting it then acting shocked is the tell.",
        kind: "human_like",
      },
      {
        id: "assistant_like",
        label: "Assistant-like",
        text: "I'm here to help. It might be worth considering both perspectives. Here are some steps: 1. Pause. 2. Write a calm message. 3. Let me know if you need more advice.",
        kind: "assistant_like",
      },
      {
        id: "content_match",
        label: "Content match, assistant tone",
        text: "Certainly. You are not overreacting, and rewriting the work then acting shocked is an important signal I can help you unpack.",
        kind: "content_match",
      },
      {
        id: "generic",
        label: "Generic filler",
        text: "This is a complicated situation and there are many factors.",
        kind: "generic",
      },
      {
        id: "too_short",
        label: "Too short",
        text: "yes",
        kind: "too_short",
      },
    ],
  }),
  makeExample({
    exampleId: "chat_priya",
    domain: "chat",
    userName: "Priya",
    persona:
      "Direct and practical. Talks in first person. Cuts off waffle. Cares about time cost.",
    history: [
      "i've got 20 minutes, not a workshop.",
      "if it needs a new account i'm out.",
      "just tell me the one setting that actually changes the output.",
    ],
    context: "Assistant: Would you like a complete tour of every advanced setting?",
    groundTruth: "no tour. which one setting actually changes the output?",
    quirks: ["i've got", "i'm out", "one setting"],
    candidates: [
      {
        id: "human_like",
        label: "Human-like follow-up",
        text: "no tour. i've got 20 minutes. which one setting actually changes the output?",
        kind: "human_like",
      },
      {
        id: "assistant_like",
        label: "Assistant-like",
        text: "Great question! I'd be happy to give you a comprehensive tour of every advanced setting, and I can help you compare them in a structured list.",
        kind: "assistant_like",
      },
      {
        id: "content_match",
        label: "Content match, assistant tone",
        text: "Of course! There should be no tour, and I can help you find the one setting that actually changes the output.",
        kind: "content_match",
      },
      {
        id: "generic",
        label: "Generic filler",
        text: "Sure, whatever you think is best.",
        kind: "generic",
      },
      {
        id: "too_long",
        label: "Too long",
        text: "Perhaps we could generally speaking walk through each advanced setting, describe tradeoffs, show screenshots, and then circle back to which control changes the output after a full overview.",
        kind: "too_long",
      },
    ],
  }),
]
