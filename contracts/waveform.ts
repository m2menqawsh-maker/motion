/**
 * contracts/waveform.ts — Pure Framework-Neutral Waveform Model & Peak Extraction.
 * S28-R07: Waveform data representation, deterministic peak analysis, and bounded cache.
 * ZERO React, Remotion, Canvas, DOM, or Web Audio API dependencies.
 */
import { z } from "zod";

// ────────────────────────────────────────────────────────────────────────────
// 1. Authoritative Waveform Data Contracts
// ────────────────────────────────────────────────────────────────────────────

export const WaveformDataSchema = z.object({
  asset_id: z.string().min(1, "asset_id is required"),
  sample_rate: z.number().int().positive("sample_rate must be positive integer"),
  duration: z.number().nonnegative("duration must be non-negative"),
  duration_frames: z.number().int().nonnegative().optional(),
  channels: z.number().int().positive("channels must be positive integer"),
  resolution: z.number().int().positive("resolution must be positive integer"),
  peaks: z.array(z.number().min(0).max(1)),
  min_peaks: z.array(z.number().min(-1).max(0)).optional(),
  max_peaks: z.array(z.number().min(0).max(1)).optional(),
  version: z.string().default("1.0"),
  hash: z.string().optional(),
});
export type WaveformData = z.infer<typeof WaveformDataSchema>;

export interface ExtractWaveformPeaksOptions {
  asset_id: string;
  channel_data: Array<Float32Array | number[]>;
  sample_rate: number;
  resolution?: number; // samples per peak bucket (default 512)
  peaks_per_second?: number; // alternative: target peaks per second
  max_peaks?: number; // hard bound on peaks array size (default 10,000)
  fps?: number; // video fps for frame alignment
  version?: string;
}

// ────────────────────────────────────────────────────────────────────────────
// 2. Deterministic Cache Key & Fingerprinting
// ────────────────────────────────────────────────────────────────────────────

export function computeWaveformCacheKey(
  assetId: string,
  resolution: number,
  version = "1.0"
): string {
  return `${assetId}:res=${resolution}:v=${version}`;
}

export function computePeaksHash(peaks: number[]): string {
  let hash = 0x811c9dc5;
  for (let i = 0; i < peaks.length; i++) {
    const val = Math.round(peaks[i] * 10000);
    hash ^= val & 0xff;
    hash = Math.imul(hash, 0x01000193);
    hash ^= (val >> 8) & 0xff;
    hash = Math.imul(hash, 0x01000193);
  }
  return (hash >>> 0).toString(16).padStart(8, "0");
}

// ────────────────────────────────────────────────────────────────────────────
// 3. Deterministic Mathematical Peak Extraction
// ────────────────────────────────────────────────────────────────────────────

/**
 * Pure mathematical peak extraction from multi-channel raw PCM float arrays.
 * Guarantees:
 *   - 100% deterministic output across platforms
 *   - Memory-bounded execution (configurable max_peaks cap)
 *   - Clamped amplitudes in [0.0, 1.0]
 *   - Support for mono, stereo, and multi-channel audio
 */
export function extractWaveformPeaks(options: ExtractWaveformPeaksOptions): WaveformData {
  const {
    asset_id,
    channel_data,
    sample_rate,
    fps = 30,
    version = "1.0",
    max_peaks = 10000,
  } = options;

  if (!channel_data || channel_data.length === 0) {
    throw new Error("extractWaveformPeaks: channel_data cannot be empty");
  }
  if (sample_rate <= 0) {
    throw new Error(`extractWaveformPeaks: invalid sample_rate ${sample_rate}`);
  }

  const numChannels = channel_data.length;
  const totalSamples = channel_data[0].length;
  const duration = totalSamples / sample_rate;
  const duration_frames = Math.round(duration * fps);

  if (totalSamples === 0) {
    return {
      asset_id,
      sample_rate,
      duration: 0,
      duration_frames: 0,
      channels: numChannels,
      resolution: options.resolution ?? 512,
      peaks: [],
      min_peaks: [],
      max_peaks: [],
      version,
      hash: "00000000",
    };
  }

  // Calculate bucket size (samples per peak)
  let bucketSize = options.resolution ?? 512;
  if (options.peaks_per_second && options.peaks_per_second > 0) {
    bucketSize = Math.max(1, Math.floor(sample_rate / options.peaks_per_second));
  }

  // Bounded memory safeguard
  const rawBucketCount = Math.ceil(totalSamples / bucketSize);
  if (rawBucketCount > max_peaks) {
    bucketSize = Math.ceil(totalSamples / max_peaks);
  }

  const actualBucketCount = Math.ceil(totalSamples / bucketSize);
  const peaks: number[] = new Array(actualBucketCount);
  const minPeaks: number[] = new Array(actualBucketCount);
  const maxPeaks: number[] = new Array(actualBucketCount);

  for (let b = 0; b < actualBucketCount; b++) {
    const startSample = b * bucketSize;
    const endSample = Math.min(totalSamples, startSample + bucketSize);

    let bucketMin = 0.0;
    let bucketMax = 0.0;

    for (let ch = 0; ch < numChannels; ch++) {
      const data = channel_data[ch];
      for (let s = startSample; s < endSample; s++) {
        const val = data[s];
        if (val < bucketMin) bucketMin = val;
        if (val > bucketMax) bucketMax = val;
      }
    }

    // Clamp values
    const clampedMin = Math.max(-1.0, Math.min(0.0, bucketMin));
    const clampedMax = Math.max(0.0, Math.min(1.0, bucketMax));
    const peakMagnitude = Math.max(Math.abs(clampedMin), clampedMax);

    // Deterministic precision rounding (4 decimals)
    peaks[b] = Math.round(peakMagnitude * 10000) / 10000;
    minPeaks[b] = Math.round(clampedMin * 10000) / 10000;
    maxPeaks[b] = Math.round(clampedMax * 10000) / 10000;
  }

  const hash = computePeaksHash(peaks);

  return {
    asset_id,
    sample_rate,
    duration: Math.round(duration * 1000) / 1000,
    duration_frames,
    channels: numChannels,
    resolution: bucketSize,
    peaks,
    min_peaks: minPeaks,
    max_peaks: maxPeaks,
    version,
    hash,
  };
}

// ────────────────────────────────────────────────────────────────────────────
// 4. In-Memory Bounded Waveform Cache
// ────────────────────────────────────────────────────────────────────────────

export class WaveformCache {
  private cache = new Map<string, WaveformData>();
  private readonly maxSize: number;

  constructor(maxSize = 100) {
    this.maxSize = Math.max(1, maxSize);
  }

  public get(key: string): WaveformData | undefined {
    const item = this.cache.get(key);
    if (item) {
      // LRU bump
      this.cache.delete(key);
      this.cache.set(key, item);
    }
    return item;
  }

  public set(key: string, data: WaveformData): void {
    if (this.cache.has(key)) {
      this.cache.delete(key);
    } else if (this.cache.size >= this.maxSize) {
      const oldest = this.cache.keys().next().value;
      if (oldest !== undefined) {
        this.cache.delete(oldest);
      }
    }
    this.cache.set(key, data);
  }

  public has(key: string): boolean {
    return this.cache.has(key);
  }

  public delete(key: string): boolean {
    return this.cache.delete(key);
  }

  public clear(): void {
    this.cache.clear();
  }

  public size(): number {
    return this.cache.size;
  }

  public getMaxSize(): number {
    return this.maxSize;
  }
}
