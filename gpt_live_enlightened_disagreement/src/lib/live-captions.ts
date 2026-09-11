export type CaptionState = {
  user: string;
  assistant: string;
};

export type TranscriptEvent = {
  type: string;
  delta?: string;
};

export function applyTranscriptDelta(
  _state: CaptionState,
  _event: TranscriptEvent,
): CaptionState {
  throw new Error("not implemented");
}
