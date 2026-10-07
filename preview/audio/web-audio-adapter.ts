/**
 * preview/audio/web-audio-adapter.ts — Web Audio API Boundary & Mock Execution Engine.
 * S28-R07: Isolates all browser Web Audio API calls behind a resilient adapter.
 * Provides complete deterministic mock implementation for headless / Node / Vitest tests.
 * ZERO React or Remotion dependencies.
 */
import { AudioDiagnosticError } from "./audio-types";

// ────────────────────────────────────────────────────────────────────────────
// 1. Mock Web Audio Primitives (for Node / Headless / Test environments)
// ────────────────────────────────────────────────────────────────────────────

export class MockAudioParam {
  public value: number;

  constructor(initialValue: number = 1.0) {
    this.value = initialValue;
  }

  public setValueAtTime(value: number, _startTime: number): void {
    this.value = value;
  }

  public linearRampToValueAtTime(value: number, _endTime: number): void {
    this.value = value;
  }
}

export class MockGainNode {
  public readonly gain: MockAudioParam;
  public connectedTo: any = null;

  constructor(initialGain: number = 1.0) {
    this.gain = new MockAudioParam(initialGain);
  }

  public connect(destination: any): void {
    this.connectedTo = destination;
  }

  public disconnect(): void {
    this.connectedTo = null;
  }
}

export class MockAudioBuffer {
  public readonly numberOfChannels: number;
  public readonly length: number;
  public readonly sampleRate: number;
  public readonly duration: number;
  private channelData: Float32Array[];

  constructor(numberOfChannels: number, length: number, sampleRate: number) {
    this.numberOfChannels = numberOfChannels;
    this.length = length;
    this.sampleRate = sampleRate;
    this.duration = length / sampleRate;
    this.channelData = [];
    for (let i = 0; i < numberOfChannels; i++) {
      this.channelData.push(new Float32Array(length));
    }
  }

  public getChannelData(channel: number): Float32Array {
    if (channel < 0 || channel >= this.numberOfChannels) {
      throw new Error(`Channel index out of bounds: ${channel}`);
    }
    return this.channelData[channel];
  }

  public copyToChannel(source: Float32Array, channel: number): void {
    this.getChannelData(channel).set(source);
  }
}

export class MockAudioBufferSourceNode {
  public buffer: MockAudioBuffer | null = null;
  public readonly playbackRate: MockAudioParam;
  public loop: boolean = false;
  public onended: ((ev: any) => void) | null = null;

  public isPlaying: boolean = false;
  public startTime: number = 0;
  public startOffset: number = 0;
  public duration?: number;
  public stoppedTime?: number;
  public connectedTo: any = null;

  constructor() {
    this.playbackRate = new MockAudioParam(1.0);
  }

  public connect(destination: any): void {
    this.connectedTo = destination;
  }

  public disconnect(): void {
    this.connectedTo = null;
  }

  public start(when = 0, offset = 0, duration?: number): void {
    if (this.isPlaying) {
      throw new Error("Cannot start an AudioBufferSourceNode that is already playing");
    }
    this.isPlaying = true;
    this.startTime = when;
    this.startOffset = offset;
    this.duration = duration;
  }

  public stop(when = 0): void {
    if (!this.isPlaying) return;
    this.isPlaying = false;
    this.stoppedTime = when;
    if (this.onended) {
      try {
        this.onended({ target: this });
      } catch (e) {
        console.error("Error in onended handler:", e);
      }
    }
  }
}

export class MockWebAudioContext {
  public currentTime: number = 0;
  public readonly sampleRate: number = 44100;
  public state: "running" | "suspended" | "closed" = "running";
  public readonly destination = {
    connect: () => {},
    disconnect: () => {},
  };

  public createGain(): MockGainNode {
    return new MockGainNode();
  }

  public createBufferSource(): MockAudioBufferSourceNode {
    return new MockAudioBufferSourceNode();
  }

  public createBuffer(numberOfChannels: number, length: number, sampleRate: number): MockAudioBuffer {
    return new MockAudioBuffer(numberOfChannels, length, sampleRate);
  }

  public async decodeAudioData(arrayBuffer: ArrayBuffer): Promise<MockAudioBuffer> {
    if (!arrayBuffer || arrayBuffer.byteLength === 0) {
      throw new AudioDiagnosticError(
        "DECODE_FAILURE",
        "Cannot decode empty or null ArrayBuffer"
      );
    }

    // Inspect if buffer has simulated corruption marker
    const uint8 = new Uint8Array(arrayBuffer);
    if (uint8.length >= 4 && uint8[0] === 0xde && uint8[1] === 0xad) {
      throw new AudioDiagnosticError(
        "DECODE_FAILURE",
        "Corrupted audio stream: invalid audio header"
      );
    }

    // Synthesize mock buffer proportional to byte size
    const durationSec = Math.max(0.1, arrayBuffer.byteLength / (44100 * 2));
    const sampleCount = Math.floor(durationSec * this.sampleRate);
    const mockBuf = new MockAudioBuffer(2, sampleCount, this.sampleRate);

    // Populate with simple sine wave
    const left = mockBuf.getChannelData(0);
    const right = mockBuf.getChannelData(1);
    for (let i = 0; i < sampleCount; i++) {
      const sample = Math.sin((2 * Math.PI * 440 * i) / this.sampleRate) * 0.5;
      left[i] = sample;
      right[i] = sample;
    }

    return mockBuf;
  }

  public async resume(): Promise<void> {
    this.state = "running";
  }

  public async suspend(): Promise<void> {
    this.state = "suspended";
  }

  public async close(): Promise<void> {
    this.state = "closed";
  }

  public advanceTime(seconds: number): void {
    if (seconds > 0) {
      this.currentTime += seconds;
    }
  }
}

// ────────────────────────────────────────────────────────────────────────────
// 2. Audio Context Factory & Detection
// ────────────────────────────────────────────────────────────────────────────

export function isNativeWebAudioSupported(): boolean {
  return (
    typeof globalThis !== "undefined" &&
    (typeof (globalThis as any).AudioContext !== "undefined" ||
      typeof (globalThis as any).webkitAudioContext !== "undefined")
  );
}

export function createWebAudioContext(options?: {
  audioContext?: any;
  forceMock?: boolean;
  failClosedIfUnavailable?: boolean;
}): any {
  if (options?.audioContext) {
    return options.audioContext;
  }

  if (options?.forceMock) {
    return new MockWebAudioContext();
  }

  if (isNativeWebAudioSupported()) {
    const Ctx = (globalThis as any).AudioContext || (globalThis as any).webkitAudioContext;
    try {
      return new Ctx();
    } catch (err: any) {
      if (options?.failClosedIfUnavailable) {
        throw new AudioDiagnosticError(
          "AUDIO_CONTEXT_UNAVAILABLE",
          `Failed to instantiate native AudioContext: ${err.message}`,
          { details: { originalError: err.message } }
        );
      }
      return new MockWebAudioContext();
    }
  }

  if (options?.failClosedIfUnavailable) {
    throw new AudioDiagnosticError(
      "AUDIO_CONTEXT_UNAVAILABLE",
      "Web Audio API (AudioContext) is not available in the current environment"
    );
  }

  // Fallback to mock context in test/headless environments
  return new MockWebAudioContext();
}

/**
 * Creates a synthetic Float32Array AudioBuffer for testing purposes.
 */
export function createSyntheticAudioBuffer(
  context: any,
  options: {
    durationSec: number;
    sampleRate?: number;
    channels?: number;
    frequency?: number;
  }
): any {
  const sampleRate = options.sampleRate ?? 44100;
  const channels = options.channels ?? 2;
  const totalSamples = Math.floor(options.durationSec * sampleRate);
  const freq = options.frequency ?? 440;

  const buf = context.createBuffer(channels, totalSamples, sampleRate);
  for (let ch = 0; ch < channels; ch++) {
    const data = buf.getChannelData(ch);
    for (let i = 0; i < totalSamples; i++) {
      data[i] = Math.sin((2 * Math.PI * freq * i) / sampleRate) * 0.7;
    }
  }
  return buf;
}
