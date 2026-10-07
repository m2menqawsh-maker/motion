/**
 * tests/remotion/s28_r07_waveform.test.ts
 * Comprehensive Verification for S28-R07 Waveform Model & Peak Extraction.
 * Tests:
 *   - Pure WaveformDataSchema validity
 *   - Mono and Stereo peak extraction
 *   - Deterministic output (identical peaks across runs)
 *   - Configurable resolution (samples per peak vs peaks per second)
 *   - Bounded memory (max_peaks cap)
 *   - Cache key generation & LRU eviction
 *   - WaveformAnalyzer integration
 */
import { describe, it, expect } from "vitest";
import {
  WaveformDataSchema,
  type WaveformData,
  extractWaveformPeaks,
  computeWaveformCacheKey,
  computePeaksHash,
  WaveformCache,
} from "../../contracts/waveform";
import { WaveformAnalyzer } from "../../preview/audio/waveform-analyzer";
import { MockAudioBuffer, MockWebAudioContext } from "../../preview/audio/web-audio-adapter";

describe("S28-R07 Waveform Model & Peak Extraction", () => {
  function generateSyntheticChannelData(
    samples: number,
    frequency: number,
    sampleRate = 44100
  ): Float32Array {
    const data = new Float32Array(samples);
    for (let i = 0; i < samples; i++) {
      data[i] = Math.sin((2 * Math.PI * frequency * i) / sampleRate);
    }
    return data;
  }

  // ──────────────────────────────────────────────────────────────────────────
  // 1. Schema & Validation
  // ──────────────────────────────────────────────────────────────────────────

  it("WAVE-01: WaveformData adheres to strict Zod schema fail-closed", () => {
    const validData: WaveformData = {
      asset_id: "audio_voice_01",
      sample_rate: 44100,
      duration: 3.5,
      duration_frames: 105,
      channels: 2,
      resolution: 512,
      peaks: [0.1, 0.45, 0.8, 0.2],
      min_peaks: [-0.1, -0.45, -0.8, -0.2],
      max_peaks: [0.1, 0.45, 0.8, 0.2],
      version: "1.0",
      hash: "1234abcd",
    };

    const parsed = WaveformDataSchema.safeParse(validData);
    expect(parsed.success).toBe(true);

    // Fail-closed on invalid peak (> 1.0 or < 0.0)
    const invalidPeak = { ...validData, peaks: [1.2] };
    expect(WaveformDataSchema.safeParse(invalidPeak).success).toBe(false);

    // Fail-closed on negative sample_rate
    const invalidSampleRate = { ...validData, sample_rate: -44100 };
    expect(WaveformDataSchema.safeParse(invalidSampleRate).success).toBe(false);
  });

  // ──────────────────────────────────────────────────────────────────────────
  // 2. Deterministic Peak Extraction (Mono & Stereo)
  // ──────────────────────────────────────────────────────────────────────────

  it("WAVE-02: Peak extraction is 100% deterministic on mono and stereo inputs", () => {
    const sampleRate = 44100;
    const sampleCount = 44100 * 2; // 2 seconds

    const left = generateSyntheticChannelData(sampleCount, 440, sampleRate);
    const right = generateSyntheticChannelData(sampleCount, 880, sampleRate);

    // Run 1 (Stereo)
    const res1 = extractWaveformPeaks({
      asset_id: "music_test_01",
      channel_data: [left, right],
      sample_rate: sampleRate,
      resolution: 512,
    });

    // Run 2 (Identical input)
    const res2 = extractWaveformPeaks({
      asset_id: "music_test_01",
      channel_data: [left, right],
      sample_rate: sampleRate,
      resolution: 512,
    });

    expect(res1.peaks.length).toBe(res2.peaks.length);
    expect(res1.peaks).toEqual(res2.peaks);
    expect(res1.hash).toBe(res2.hash);
    expect(res1.channels).toBe(2);
    expect(res1.duration).toBe(2.0);

    // Run 3 (Mono)
    const monoRes = extractWaveformPeaks({
      asset_id: "voice_mono_01",
      channel_data: [left],
      sample_rate: sampleRate,
      resolution: 512,
    });
    expect(monoRes.channels).toBe(1);
    expect(monoRes.peaks.length).toBe(res1.peaks.length);
  });

  // ──────────────────────────────────────────────────────────────────────────
  // 3. Configurable Resolution
  // ──────────────────────────────────────────────────────────────────────────

  it("WAVE-03: Configurable resolution supports samples_per_peak and peaks_per_second", () => {
    const sampleRate = 44100;
    const sampleCount = 44100 * 3; // 3 seconds
    const data = [generateSyntheticChannelData(sampleCount, 300, sampleRate)];

    // Resolution mode A: samples per peak = 1024
    const resA = extractWaveformPeaks({
      asset_id: "res_test_A",
      channel_data: data,
      sample_rate: sampleRate,
      resolution: 1024,
    });
    const expectedBucketsA = Math.ceil(sampleCount / 1024);
    expect(resA.peaks.length).toBe(expectedBucketsA);
    expect(resA.resolution).toBe(1024);

    // Resolution mode B: 100 peaks per second
    const resB = extractWaveformPeaks({
      asset_id: "res_test_B",
      channel_data: data,
      sample_rate: sampleRate,
      peaks_per_second: 100,
    });
    // For 3 seconds at 100 peaks/sec, expect ~300 peaks
    expect(resB.peaks.length).toBeGreaterThanOrEqual(299);
    expect(resB.peaks.length).toBeLessThanOrEqual(301);
  });

  // ──────────────────────────────────────────────────────────────────────────
  // 4. Bounded Memory Safeguard
  // ──────────────────────────────────────────────────────────────────────────

  it("WAVE-04: Bounded memory — peak count never exceeds max_peaks cap", () => {
    const sampleRate = 44100;
    const sampleCount = 44100 * 60; // 60 seconds of audio (2,646,000 samples)
    const data = [new Float32Array(sampleCount)];

    // If resolution was 10 samples per peak, it would generate 264,600 peaks!
    // But max_peaks = 500 should force bucket size up
    const res = extractWaveformPeaks({
      asset_id: "long_audio",
      channel_data: data,
      sample_rate: sampleRate,
      resolution: 10,
      max_peaks: 500,
    });

    expect(res.peaks.length).toBeLessThanOrEqual(500);
  });

  // ──────────────────────────────────────────────────────────────────────────
  // 5. WaveformCache & Keying
  // ──────────────────────────────────────────────────────────────────────────

  it("WAVE-05: WaveformCache enforces deterministic keys and bounded LRU eviction", () => {
    const key = computeWaveformCacheKey("bgm_corporate", 512, "1.0");
    expect(key).toBe("bgm_corporate:res=512:v=1.0");

    const cache = new WaveformCache(3); // max 3 entries

    const mockItem = (id: string): WaveformData => ({
      asset_id: id,
      sample_rate: 44100,
      duration: 1.0,
      channels: 1,
      resolution: 512,
      peaks: [0.5],
      version: "1.0",
      hash: "abc",
    });

    cache.set("item1", mockItem("item1"));
    cache.set("item2", mockItem("item2"));
    cache.set("item3", mockItem("item3"));
    expect(cache.size()).toBe(3);

    // Access item1 to bump it
    expect(cache.get("item1")?.asset_id).toBe("item1");

    // Add item4 -> item2 (oldest unaccessed) should be evicted
    cache.set("item4", mockItem("item4"));
    expect(cache.size()).toBe(3);
    expect(cache.has("item1")).toBe(true);
    expect(cache.has("item2")).toBe(false);
    expect(cache.has("item4")).toBe(true);
  });

  // ──────────────────────────────────────────────────────────────────────────
  // 6. WaveformAnalyzer Integration
  // ──────────────────────────────────────────────────────────────────────────

  it("WAVE-06: WaveformAnalyzer bridges MockAudioBuffer and cached extraction", async () => {
    const analyzer = new WaveformAnalyzer();
    const ctx = new MockWebAudioContext();

    const mockBuffer = new MockAudioBuffer(2, 44100, 44100);
    const left = mockBuffer.getChannelData(0);
    for (let i = 0; i < 44100; i++) {
      left[i] = 0.8;
    }

    const waveform = analyzer.analyzeAudioBuffer("test_asset_01", mockBuffer, { resolution: 1000 });
    expect(waveform.asset_id).toBe("test_asset_01");
    expect(waveform.peaks[0]).toBe(0.8);

    // Second call hits cache
    const cached = analyzer.getCached("test_asset_01", 1000);
    expect(cached).toBe(waveform);
  });
});
