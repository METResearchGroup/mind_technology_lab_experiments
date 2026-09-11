export const PRINCIPLES_FILE_NAME = "ENLIGHTENED_DISAGREEMENT_PRINCIPLES.md";
export const PRINCIPLES_MISSING_ERROR =
  "ENLIGHTENED_DISAGREEMENT_PRINCIPLES.md is missing";
export const PRINCIPLES_TITLE = "# Enlightened disagreement principles";

export const OPERATING_RULES_HEADING = "## Operating rules";
export const DEVILS_ADVOCATE_HEADING = "## Devil's advocate procedure";
export const MISSION_HEADING = "## Mission";
export const NON_GOALS_HEADING = "## Non-goals";

export const OPERATING_RULE_NAMES = [
  "Keep the disagreement",
  "Hard on the issues, soft on the person",
  "Make the gap accurate before you make it dramatic",
  "Stop caricature and dehumanization",
  "Repeat the other person's claim before you rebut it",
  "Listen to understand, not only to reply",
  "Self-distance when moral heat rises",
  "Demand the strongest case against each speaker's own view",
  "Move from positions to interests",
  "Set engagement rules before the heat",
  "Fight the real disagreement, not a cartoon of the other side",
  "Invite dissent inside each camp, not only across camps",
] as const;

export function principlesFilePath(cwd = process.cwd()): string {
  throw new Error("not implemented");
}

export function readPrinciplesMarkdown(_cwd = process.cwd()): string {
  throw new Error("not implemented");
}
