/**
 * OpenAI Realtime WebRTC voice — CCv2 frontend (vanilla JS).
 *
 * Persists RTCPeerConnection across Streamlit reruns via WeakMap keyed by
 * parentElement. State syncs to Python through setStateValue.
 */

const REALTIME_CALLS_URL = "https://api.openai.com/v1/realtime/calls";
const TRANSCRIPT_SYNC_MS = 80;

/** @type {WeakMap<HTMLElement, InstanceState>} */
const instances = new WeakMap();

/**
 * @typedef {object} InstanceState
 * @property {RTCPeerConnection | null} pc
 * @property {RTCDataChannel | null} dc
 * @property {MediaStream | null} localStream
 * @property {HTMLAudioElement | null} audioEl
 * @property {boolean} connecting
 * @property {{ role: string, text: string, partial?: boolean }[]} transcripts
 * @property {string | null} transcriptionModel
 * @property {ReturnType<typeof setTimeout> | 0} transcriptSyncTimer
 * @property {string | null} activeAssistantResponseId
 * @property {"legacy" | "ga" | null} assistantDeltaStream
 * @property {Set<string>} completedAssistantResponseIds
 */

/** @param {HTMLElement} parentElement */
function getInstance(parentElement) {
  let inst = instances.get(parentElement);
  if (!inst) {
    inst = {
      pc: null,
      dc: null,
      localStream: null,
      audioEl: null,
      connecting: false,
      transcripts: [],
      transcriptionModel: null,
      transcriptSyncTimer: 0,
      activeAssistantResponseId: null,
      assistantDeltaStream: null,
      completedAssistantResponseIds: new Set(),
    };
    instances.set(parentElement, inst);
  }
  return inst;
}

/**
 * @param {{ role: string, text: string }[]} fromPython
 * @param {{ role: string, text: string }[]} local
 */
function mergeTranscripts(fromPython, local) {
  if (!Array.isArray(fromPython) || fromPython.length === 0) {
    return local;
  }
  if (!Array.isArray(local) || local.length === 0) {
    return fromPython.slice();
  }
  if (local.length > fromPython.length) {
    return local;
  }
  if (fromPython.length > local.length) {
    return fromPython.slice();
  }
  const lastLocal = local[local.length - 1];
  const lastPython = fromPython[fromPython.length - 1];
  if (
    lastLocal &&
    lastPython &&
    lastLocal.role === lastPython.role &&
    String(lastLocal.text || "").length >= String(lastPython.text || "").length
  ) {
    return local;
  }
  return fromPython.slice();
}

/**
 * @param {InstanceState["transcripts"]} lines
 * @returns {InstanceState["transcripts"]}
 */
function copyTranscripts(lines) {
  return lines.map((line) => ({
    role: line.role,
    text: line.text,
    partial: Boolean(line.partial),
  }));
}

/**
 * @param {InstanceState} inst
 * @param {(key: string, value: unknown) => void} setStateValue
 */
function pushTranscriptsToPython(inst, setStateValue) {
  setStateValue("transcripts", copyTranscripts(inst.transcripts));
}

/**
 * @param {InstanceState} inst
 * @param {(key: string, value: unknown) => void} setStateValue
 * @param {boolean} immediate
 */
function scheduleTranscriptSync(inst, setStateValue, immediate) {
  if (inst.transcriptSyncTimer) {
    clearTimeout(inst.transcriptSyncTimer);
    inst.transcriptSyncTimer = 0;
  }
  if (immediate) {
    pushTranscriptsToPython(inst, setStateValue);
    return;
  }
  inst.transcriptSyncTimer = setTimeout(() => {
    inst.transcriptSyncTimer = 0;
    pushTranscriptsToPython(inst, setStateValue);
  }, TRANSCRIPT_SYNC_MS);
}

/**
 * @param {InstanceState} inst
 * @param {(key: string, value: unknown) => void} setStateValue
 * @param {"user" | "assistant"} role
 * @param {string} delta
 */
function applyTranscriptDelta(inst, setStateValue, role, delta) {
  if (!delta) return;
  const last = inst.transcripts[inst.transcripts.length - 1];
  if (last && last.role === role && last.partial) {
    last.text += delta;
    inst.transcripts = inst.transcripts.slice();
  } else {
    inst.transcripts = [...inst.transcripts, { role, text: delta, partial: true }];
  }
  scheduleTranscriptSync(inst, setStateValue, false);
}

/**
 * @param {InstanceState} inst
 * @param {(key: string, value: unknown) => void} setStateValue
 * @param {"user" | "assistant"} role
 * @param {string} text
 */
function finalizeTranscript(inst, setStateValue, role, text) {
  const trimmed = text.trim();
  const last = inst.transcripts[inst.transcripts.length - 1];
  if (last && last.role === role) {
    if (!last.partial && last.text === trimmed) {
      return;
    }
    last.text = trimmed || last.text.trim();
    last.partial = false;
    if (!last.text) return;
    inst.transcripts = inst.transcripts.slice();
  } else if (trimmed) {
    inst.transcripts = [
      ...inst.transcripts,
      { role, text: trimmed, partial: false },
    ];
  } else {
    return;
  }
  scheduleTranscriptSync(inst, setStateValue, true);
}

/**
 * @param {unknown} response
 * @returns {string}
 */
function assistantTranscriptFromResponse(response) {
  if (!response || typeof response !== "object") return "";
  const output = /** @type {Record<string, unknown>} */ (response).output;
  if (!Array.isArray(output)) return "";
  const parts = [];
  for (const item of output) {
    if (!item || typeof item !== "object") continue;
    const message = /** @type {Record<string, unknown>} */ (item);
    if (message.type !== "message" || !Array.isArray(message.content)) continue;
    for (const part of message.content) {
      if (!part || typeof part !== "object") continue;
      const content = /** @type {Record<string, unknown>} */ (part);
      if (content.type === "audio" && typeof content.transcript === "string") {
        parts.push(content.transcript);
      }
      if (content.type === "text" && typeof content.text === "string") {
        parts.push(content.text);
      }
    }
  }
  return parts.join("").trim();
}

/**
 * @param {Record<string, unknown>} msg
 * @returns {string | null}
 */
function responseIdFromEvent(msg) {
  if (typeof msg.response_id === "string") return msg.response_id;
  const response = msg.response;
  if (response && typeof response === "object") {
    const id = /** @type {Record<string, unknown>} */ (response).id;
    if (typeof id === "string") return id;
  }
  return null;
}

/**
 * @param {InstanceState} inst
 * @param {string | null} responseId
 */
function beginAssistantResponse(inst, responseId) {
  if (!responseId) return;
  if (inst.activeAssistantResponseId === responseId) return;
  inst.activeAssistantResponseId = responseId;
  inst.assistantDeltaStream = null;
}

/**
 * @param {InstanceState} inst
 * @param {string | null} responseId
 * @returns {boolean}
 */
function shouldIgnoreAssistantDelta(inst, responseId) {
  if (!responseId) return false;
  if (inst.completedAssistantResponseIds.has(responseId)) return true;
  return (
    inst.activeAssistantResponseId !== null &&
    inst.activeAssistantResponseId !== responseId
  );
}

/**
 * @param {InstanceState} inst
 * @param {string} type
 * @param {string | null} responseId
 * @returns {boolean}
 */
function shouldApplyAssistantDelta(inst, type, responseId) {
  if (!responseId) return true;
  beginAssistantResponse(inst, responseId);
  if (shouldIgnoreAssistantDelta(inst, responseId)) return false;

  const stream =
    type === "response.audio_transcript.delta"
      ? "legacy"
      : type === "response.output_audio_transcript.delta"
        ? "ga"
        : null;
  if (!stream) return true;

  if (!inst.assistantDeltaStream) {
    inst.assistantDeltaStream = stream;
    return true;
  }
  return inst.assistantDeltaStream === stream;
}

/**
 * @param {InstanceState} inst
 * @param {string | null} responseId
 */
function completeAssistantResponse(inst, responseId) {
  if (responseId) {
    inst.completedAssistantResponseIds.add(responseId);
  }
  if (!responseId || inst.activeAssistantResponseId === responseId) {
    inst.activeAssistantResponseId = null;
    inst.assistantDeltaStream = null;
  }
}

/**
 * @param {unknown} item
 * @returns {string | null}
 */
function userTranscriptFromItem(item) {
  if (!item || typeof item !== "object") return null;
  const message = /** @type {Record<string, unknown>} */ (item);
  if (message.role !== "user" || !Array.isArray(message.content)) return null;
  for (const part of message.content) {
    if (!part || typeof part !== "object") continue;
    const content = /** @type {Record<string, unknown>} */ (part);
    if (
      (content.type === "input_audio" || content.type === "audio") &&
      typeof content.transcript === "string"
    ) {
      return content.transcript;
    }
  }
  return null;
}

/**
 * @param {Record<string, unknown>} msg
 * @param {InstanceState} inst
 * @param {(key: string, value: unknown) => void} setStateValue
 */
function handleRealtimeEvent(msg, inst, setStateValue) {
  const type = msg.type;
  if (typeof type !== "string") return;

  if (
    type === "conversation.item.input_audio_transcription.delta" ||
    type === "conversation.item.audio_transcription.delta" ||
    type === "input_audio_transcription.delta"
  ) {
    if (typeof msg.delta === "string") {
      applyTranscriptDelta(inst, setStateValue, "user", msg.delta);
    }
    return;
  }

  if (
    type === "response.audio_transcript.delta" ||
    type === "response.output_audio_transcript.delta" ||
    type === "response.output_text.delta"
  ) {
    const responseId = responseIdFromEvent(msg);
    if (
      typeof msg.delta === "string" &&
      shouldApplyAssistantDelta(inst, type, responseId)
    ) {
      applyTranscriptDelta(inst, setStateValue, "assistant", msg.delta);
    }
    return;
  }

  if (
    type === "conversation.item.input_audio_transcription.completed" ||
    type === "conversation.item.audio_transcription.completed" ||
    type === "input_audio_transcription.completed"
  ) {
    const transcript = msg.transcript;
    if (typeof transcript === "string") {
      finalizeTranscript(inst, setStateValue, "user", transcript);
    }
    return;
  }

  if (type === "conversation.item.done" || type === "conversation.item.added") {
    const fromItem = userTranscriptFromItem(msg.item);
    if (fromItem) {
      finalizeTranscript(inst, setStateValue, "user", fromItem);
    }
    return;
  }

  if (
    type === "response.audio_transcript.done" ||
    type === "response.output_audio_transcript.done"
  ) {
    // Per content-part events: keep accumulating via deltas; finalize on response.done.
    return;
  }

  if (type === "response.done") {
    const response = msg.response;
    const responseId = responseIdFromEvent(msg);
    if (response && typeof response === "object") {
      let transcript = assistantTranscriptFromResponse(response);
      if (!transcript) {
        const last = inst.transcripts[inst.transcripts.length - 1];
        if (last && last.role === "assistant" && last.partial) {
          transcript = last.text.trim();
        }
      }
      if (transcript) {
        finalizeTranscript(inst, setStateValue, "assistant", transcript);
      }
    }
    completeAssistantResponse(inst, responseId);
    return;
  }

  if (type === "error") {
    const err = msg.error;
    let message = "Realtime API error";
    if (err && typeof err === "object" && typeof err.message === "string") {
      message = err.message;
    } else if (typeof err === "string") {
      message = err;
    }
    setStateValue("error", message);
  }
}

/**
 * @param {InstanceState} inst
 * @param {(key: string, value: unknown) => void} setStateValue
 */
async function teardown(inst, setStateValue) {
  if (inst.transcriptSyncTimer) {
    clearTimeout(inst.transcriptSyncTimer);
    inst.transcriptSyncTimer = 0;
  }
  if (inst.dc) {
    try {
      inst.dc.close();
    } catch {
      /* ignore */
    }
    inst.dc = null;
  }
  if (inst.pc) {
    try {
      inst.pc.close();
    } catch {
      /* ignore */
    }
    inst.pc = null;
  }
  if (inst.localStream) {
    for (const track of inst.localStream.getTracks()) {
      track.stop();
    }
    inst.localStream = null;
  }
  if (inst.audioEl) {
    inst.audioEl.srcObject = null;
  }
  inst.connecting = false;
  setStateValue("connected", false);
}

/**
 * @param {InstanceState} inst
 * @param {string} clientSecret
 * @param {(key: string, value: unknown) => void} setStateValue
 */
async function startConnection(inst, clientSecret, setStateValue) {
  if (inst.pc || inst.connecting) return;

  inst.connecting = true;
  setStateValue("error", null);

  try {
    const pc = new RTCPeerConnection();
    inst.pc = pc;

    pc.ontrack = (event) => {
      const audioEl = inst.audioEl;
      const stream = event.streams && event.streams[0];
      if (!audioEl || !stream) return;
      audioEl.srcObject = stream;
      audioEl.autoplay = true;
      void audioEl.play().catch(() => {
        /* autoplay may require prior user gesture */
      });
    };

    pc.onconnectionstatechange = () => {
      const state = pc.connectionState;
      if (state === "connected") {
        setStateValue("connected", true);
        setStateValue("error", null);
      } else if (state === "failed") {
        setStateValue("error", `WebRTC connection ${state}`);
        void teardown(inst, setStateValue);
      } else if (state === "closed" || state === "disconnected") {
        setStateValue("connected", false);
      }
    };

    const localStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    inst.localStream = localStream;
    for (const track of localStream.getTracks()) {
      pc.addTrack(track, localStream);
    }

    const dc = pc.createDataChannel("oai-events");
    inst.dc = dc;

    dc.onopen = () => {
      setStateValue("connected", true);
      setStateValue("error", null);
      const transcriptionModel =
        inst.transcriptionModel || "gpt-live-transcribe";
      try {
        dc.send(
          JSON.stringify({
            type: "session.update",
            session: {
              type: "realtime",
              audio: {
                input: {
                  transcription: { model: transcriptionModel },
                  turn_detection: { type: "semantic_vad" },
                },
              },
            },
          }),
        );
      } catch {
        /* channel may already be closing */
      }
    };

    dc.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        handleRealtimeEvent(msg, inst, setStateValue);
      } catch {
        /* ignore malformed payloads */
      }
    };

    const offer = await pc.createOffer();
    await pc.setLocalDescription(offer);

    const response = await fetch(REALTIME_CALLS_URL, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${clientSecret}`,
        "Content-Type": "application/sdp",
      },
      body: offer.sdp,
    });

    if (!response.ok) {
      const detail = await response.text();
      throw new Error(
        `Realtime call failed (${response.status}): ${detail.slice(0, 500)}`,
      );
    }

    const answerSdp = await response.text();
    await pc.setRemoteDescription({ type: "answer", sdp: answerSdp });
    setStateValue("connected", true);
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    setStateValue("error", message);
    await teardown(inst, setStateValue);
  } finally {
    inst.connecting = false;
  }
}

/**
 * Re-attach remote audio after a Streamlit rerun recreates the <audio> node.
 * @param {InstanceState} inst
 */
function reattachRemoteAudio(inst) {
  const pc = inst.pc;
  const audioEl = inst.audioEl;
  if (!pc || !audioEl || pc.connectionState !== "connected") return;

  const receivers = pc.getReceivers();
  for (const receiver of receivers) {
    const track = receiver.track;
    if (track && track.kind === "audio" && track.readyState === "live") {
      const stream = new MediaStream([track]);
      audioEl.srcObject = stream;
      audioEl.autoplay = true;
      void audioEl.play().catch(() => {});
      return;
    }
  }
}

/**
 * @param {HTMLButtonElement | null} connectBtn
 * @param {HTMLButtonElement | null} disconnectBtn
 * @param {HTMLElement | null} statusEl
 * @param {boolean} connected
 * @param {boolean} connecting
 * @param {string | null | undefined} error
 */
function refreshControls(connectBtn, disconnectBtn, statusEl, connected, connecting, error) {
  if (connectBtn) {
    connectBtn.disabled = connected || connecting;
  }
  if (disconnectBtn) {
    disconnectBtn.disabled = !connected && !connecting;
  }
  if (statusEl) {
    let status = "Disconnected";
    if (connecting) status = "Connecting…";
    else if (connected) status = "Connected — speak to the assistant";
    if (error) status = `Error: ${error}`;
    statusEl.textContent = status;
  }
}

export default function mount(component) {
  const { parentElement, data, setStateValue } = component;
  if (!parentElement) return () => {};

  const connectBtn = parentElement.querySelector("#wv-connect");
  const disconnectBtn = parentElement.querySelector("#wv-disconnect");
  const statusEl = parentElement.querySelector("#wv-status");
  const audioEl = parentElement.querySelector("#wv-remote-audio");

  const inst = getInstance(parentElement);
  inst.audioEl = audioEl;

  const fromPython = data && data.transcripts;
  inst.transcripts = mergeTranscripts(fromPython, inst.transcripts);
  const transcriptionModel = data && data.transcriptionModel;
  inst.transcriptionModel =
    typeof transcriptionModel === "string" && transcriptionModel
      ? transcriptionModel
      : inst.transcriptionModel;

  const connected = Boolean(data && data.connected);
  const connecting = inst.connecting;
  const error =
    data && typeof data.error === "string" && data.error ? data.error : null;

  refreshControls(connectBtn, disconnectBtn, statusEl, connected || Boolean(inst.pc), connecting, error);
  reattachRemoteAudio(inst);

  if (connectBtn) {
    connectBtn.onclick = () => {
      const secret = data && data.clientSecret;
      if (typeof secret !== "string" || !secret.startsWith("ek_")) {
        setStateValue("error", "Missing or invalid ephemeral client secret (ek_…)");
        return;
      }
      void startConnection(inst, secret, setStateValue);
    };
  }

  if (disconnectBtn) {
    disconnectBtn.onclick = () => {
      void teardown(inst, setStateValue);
    };
  }

  return () => {
    if (connectBtn) connectBtn.onclick = null;
    if (disconnectBtn) disconnectBtn.onclick = null;
  };
}
