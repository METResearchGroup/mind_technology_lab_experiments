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
  state: CaptionState,
  event: TranscriptEvent,
): CaptionState {
  const delta = event.delta ?? "";
  if (event.type === INPUT_TRANSCRIPT_DELTA) {
    return { user: state.user + delta, assistant: state.assistant };
  }
  if (event.type === OUTPUT_TRANSCRIPT_DELTA) {
    return { user: state.user, assistant: state.assistant + delta };
  }
  return state;
}
