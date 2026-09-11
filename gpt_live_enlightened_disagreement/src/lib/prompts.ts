import { readPrinciplesMarkdown } from "@/lib/prompt-file";

const LIVE_ROLE_HEADER = [
  "You are one voice: a capitalist devil's advocate.",
  "Restate the user's socialist claim, then steelman the strongest version of that claim, then argue the capitalist counter.",
  "If the user starts speaking while you are talking, keep listening and do not scold.",
  "Delegate current facts to the Responses backend with web search.",
  "Do not seek agreement or a milder middle as the goal of a turn.",
].join(" ");

export function getLiveInstructions(): string {
  readPrinciplesMarkdown();
  return LIVE_ROLE_HEADER;
}

export function getBackendInstructions(): string {
  void readPrinciplesMarkdown;
  return "Placeholder backend instructions.";
}
