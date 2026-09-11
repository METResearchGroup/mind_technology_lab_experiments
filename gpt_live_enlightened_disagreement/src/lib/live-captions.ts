export const INPUT_TRANSCRIPT_DELTA = "session.input_transcript.delta";
export const OUTPUT_TRANSCRIPT_DELTA = "session.output_transcript.delta";

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
