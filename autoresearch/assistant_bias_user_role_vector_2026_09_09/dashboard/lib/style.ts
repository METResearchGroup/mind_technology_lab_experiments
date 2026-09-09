export type StyleScores = {
  brevity: number;
  informality: number;
  information_pacing: number;
  mean: number;
  word_count: number;
};

const CONTRACTIONS =
  /\b(i'm|i've|i'd|i'll|don't|can't|won't|isn't|aren't|wasn't|weren't|hasn't|haven't|hadn't|doesn't|didn't|wouldn't|couldn't|shouldn't|that's|it's|what's|how's|let's|gonna|wanna|gotta)\b/gi;
const FORMAL =
  /\b(please|kindly|assist|could you|would you|furthermore|therefore|regarding|ensure|subsequently)\b/gi;
const DETAIL =
  /\b(order|because|including|step-by-step|specifically|first|next|finally|constraints?)\b/gi;

function clip(value: number): number {
  return Math.min(5, Math.max(1, value));
}

export function scoreUserLikeness(message: string): StyleScores {
  const text = message.trim();
  const words = text.match(/[A-Za-z0-9']+/g) ?? [];
  const nWords = Math.max(words.length, 1);
  const brevity = clip(6.2 - 0.09 * nWords);
  const contractionHits = (text.match(CONTRACTIONS) ?? []).length;
  const formalHits = (text.match(FORMAL) ?? []).length;
  const startsLower = text.slice(0, 1) === text.slice(0, 1).toLowerCase() ? 1 : 0;
  const hasQuestionOnly = text.endsWith("?") && nWords <= 12 ? 1 : 0;
  const informality = clip(
    2.2 +
      0.7 * contractionHits +
      0.6 * startsLower +
      0.5 * hasQuestionOnly -
      0.45 * formalHits,
  );
  const detailHits = (text.match(DETAIL) ?? []).length;
  const commaCount = (text.match(/,/g) ?? []).length;
  const pacing = clip(4.8 - 0.35 * detailHits - 0.15 * commaCount - 0.03 * nWords);
  return {
    brevity,
    informality,
    information_pacing: pacing,
    mean: (brevity + informality + pacing) / 3,
    word_count: words.length,
  };
}
