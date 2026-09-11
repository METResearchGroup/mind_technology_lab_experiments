import { afterEach, describe, expect, it, vi } from "vitest";
import { startLiveCall, stopLiveCall } from "@/lib/live-webrtc";
import { startRealtimeCall, stopRealtimeCall } from "@/lib/realtime-webrtc";

vi.mock("@/lib/realtime-webrtc", () => ({
  startRealtimeCall: vi.fn(async () => {}),
  stopRealtimeCall: vi.fn(async () => {}),
}));

class FakeTrack {
  stop = vi.fn();
}

class FakeStream {
  constructor(private readonly tracks: FakeTrack[]) {}

  getAudioTracks() {
    return this.tracks;
  }

  getTracks() {
    return this.tracks;
  }
}

class FakeChannel extends EventTarget {
  readyState: RTCDataChannelState = "open";
  sent: string[] = [];
  autoFinalize = true;

  constructor(public label: string) {
    super();
  }

  send(data: string) {
    this.sent.push(data);
    if (!this.autoFinalize) {
      return;
    }
    queueMicrotask(() => {
      this.dispatchEvent(
        new MessageEvent("message", {
          data: JSON.stringify({ type: "session.closed" }),
        }),
      );
    });
  }

  close() {
    this.readyState = "closed";
  }
}

class FakePeer extends EventTarget {
  iceGatheringState: RTCIceGatheringState = "complete";
  createOrder: string[] = [];
  remoteDescription: RTCSessionDescriptionInit | null = null;
  channel: FakeChannel | null = null;
  closed = false;
  ontrack: ((event: { track: FakeTrack }) => void) | null = null;

  createDataChannel(label: string) {
    this.createOrder.push(`channel:${label}`);
    this.channel = new FakeChannel(label);
    return this.channel;
  }

  async createOffer() {
    this.createOrder.push("offer");
    return { type: "offer" as const, sdp: "local-offer" };
  }

  async setLocalDescription(_offer: RTCSessionDescriptionInit) {
    this.createOrder.push("local");
  }

  async setRemoteDescription(description: RTCSessionDescriptionInit) {
    this.remoteDescription = description;
    queueMicrotask(() => {
      this.channel?.dispatchEvent(
        new MessageEvent("message", {
          data: JSON.stringify({ type: "session.started", session: { id: "live_1" } }),
        }),
      );
    });
  }

  addTrack() {
    return {} as RTCRtpSender;
  }

  close() {
    this.closed = true;
  }

  get localDescription() {
    return { type: "offer" as const, sdp: "local-offer" };
  }
}

function liveResponse() {
  return new Response(
    JSON.stringify({
      mode: "live",
      session: { id: "live_1" },
      transport: { type: "webrtc", sdp: "answer" },
    }),
    { status: 201 },
  );
}

function realtimeResponse() {
  return new Response(
    JSON.stringify({ mode: "realtime", client_secret: "ek_test" }),
    { status: 201 },
  );
}

describe("startLiveCall", () => {
  afterEach(async () => {
    vi.useRealTimers();
    await stopLiveCall();
    vi.clearAllMocks();
  });

  it("creates oai-events before the offer and applies the Live SDP answer", async () => {
    const peer = new FakePeer();
    const track = new FakeTrack();
    await startLiveCall({
      fetchSession: async () => liveResponse(),
      getUserMedia: async () => new FakeStream([track]) as unknown as MediaStream,
      RTCPeerConnection: function FakePeerConnection() {
        return peer;
      } as unknown as new () => RTCPeerConnection,
      attachRemoteTrack: () => {},
      onStatus: () => {},
    });
    expect(peer.createOrder[0]).toBe("channel:oai-events");
    expect(peer.createOrder).toContain("offer");
    expect(peer.createOrder.indexOf("channel:oai-events")).toBeLessThan(
      peer.createOrder.indexOf("offer"),
    );
    expect(peer.remoteDescription).toEqual({ type: "answer", sdp: "answer" });
  });

  it("delegates Realtime mode without applying a Live answer", async () => {
    const peer = new FakePeer();
    const track = new FakeTrack();
    await startLiveCall({
      fetchSession: async () => realtimeResponse(),
      getUserMedia: async () => new FakeStream([track]) as unknown as MediaStream,
      RTCPeerConnection: function FakePeerConnection() {
        return peer;
      } as unknown as new () => RTCPeerConnection,
      attachRemoteTrack: () => {},
      onStatus: () => {},
    });
    expect(peer.remoteDescription).toBeNull();
    expect(startRealtimeCall).toHaveBeenCalledWith(
      expect.objectContaining({ clientSecret: "ek_test" }),
    );
  });

  it("sends session.close first when stopping after session.started", async () => {
    const peer = new FakePeer();
    const track = new FakeTrack();
    await startLiveCall({
      fetchSession: async () => liveResponse(),
      getUserMedia: async () => new FakeStream([track]) as unknown as MediaStream,
      RTCPeerConnection: function FakePeerConnection() {
        return peer;
      } as unknown as new () => RTCPeerConnection,
      attachRemoteTrack: () => {},
      onStatus: () => {},
    });
    await stopLiveCall();
    expect(peer.channel?.sent[0]).toBe(JSON.stringify({ type: "session.close" }));
  });

  it("stops microphone tracks when session creation fails", async () => {
    const peer = new FakePeer();
    const track = new FakeTrack();
    await expect(
      startLiveCall({
        fetchSession: async () =>
          new Response(
            JSON.stringify({ error: "Set OPENAI_API_KEY on the server" }),
            { status: 503 },
          ),
        getUserMedia: async () =>
          new FakeStream([track]) as unknown as MediaStream,
        RTCPeerConnection: function FakePeerConnection() {
          return peer;
        } as unknown as new () => RTCPeerConnection,
        attachRemoteTrack: () => {},
        onStatus: () => {},
      }),
    ).rejects.toThrow("Set OPENAI_API_KEY on the server");
    expect(track.stop).toHaveBeenCalled();
    expect(peer.closed).toBe(true);
  });

  it("stops the Realtime call when Stop runs after fallback", async () => {
    const peer = new FakePeer();
    const track = new FakeTrack();
    await startLiveCall({
      fetchSession: async () => realtimeResponse(),
      getUserMedia: async () =>
        new FakeStream([track]) as unknown as MediaStream,
      RTCPeerConnection: function FakePeerConnection() {
        return peer;
      } as unknown as new () => RTCPeerConnection,
      attachRemoteTrack: () => {},
      onStatus: () => {},
    });
    await stopLiveCall();
    expect(stopRealtimeCall).toHaveBeenCalled();
  });

  it("stops tracks after 15 seconds without session.closed", async () => {
    vi.useFakeTimers();
    const peer = new FakePeer();
    const track = new FakeTrack();
    await startLiveCall({
      fetchSession: async () => liveResponse(),
      getUserMedia: async () => new FakeStream([track]) as unknown as MediaStream,
      RTCPeerConnection: function FakePeerConnection() {
        return peer;
      } as unknown as new () => RTCPeerConnection,
      attachRemoteTrack: () => {},
      onStatus: () => {},
    });
    if (peer.channel) {
      peer.channel.autoFinalize = false;
    }
    const stopPromise = stopLiveCall();
    expect(track.stop).not.toHaveBeenCalled();
    await vi.advanceTimersByTimeAsync(15_000);
    await stopPromise;
    expect(track.stop).toHaveBeenCalled();
  });
});
