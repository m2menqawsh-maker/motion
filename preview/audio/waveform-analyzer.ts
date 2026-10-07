/**
 * preview/audio/waveform-analyzer.ts — Waveform Peak Analysis & Caching Subsystem.
 * S28-R07: Bridges audio buffers to the authoritative WaveformData contract.
 * ZERO React or Remotion dependencies.
 */
import {
  type WaveformData,
  extractWaveformPeaks,
  computeWaveformCacheKey,
  WaveformCache,
} from "../../contracts/waveform";

export interface AnalyzeWaveformOptions {
  resolution?: number; // samples per peak bucket (default 512)
  peaks_per_second?: number; // e.g. 100 peaks per second
  max_peaks?: number; // max peaks to bound memory (default 10,000)
  fps?: number;
  version?: string;
  bypassCache?: boolean;
}

export class WaveformAnalyzer {
  private cache: WaveformCache;

  constructor(maxCacheEntries = 100) {
    this.cache = new WaveformCache(maxCacheEntries);
  }

  /**
   * Generates or retrieves cached WaveformData from a decoded AudioBuffer (or MockAudioBuffer).
   */
  public analyzeAudioBuffer(
    assetId: string,
    audioBuffer: any,
    options?: AnalyzeWaveformOptions
  ): WaveformData {
    const resolution = options?.resolution ?? 512;
    const version = options?.version ?? "1.0";
    const cacheKey = computeWaveformCacheKey(assetId, resolution, version);

    if (!options?.bypassCache) {
      const cached = this.cache.get(cacheKey);
      if (cached) {
        return cached;
      }
    }

    const numberOfChannels = audioBuffer.numberOfChannels ?? 1;
    const channelData: Float32Array[] = [];
    for (let i = 0; i < numberOfChannels; i++) {
      channelData.push(audioBuffer.getChannelData(i));
    }

    const data = extractWaveformPeaks({
      asset_id: assetId,
      channel_data: channelData,
      sample_rate: audioBuffer.sampleRate,
      resolution,
      peaks_per_second: options?.peaks_per_second,
      max_peaks: options?.max_peaks ?? 10000,
      fps: options?.fps ?? 30,
      version,
    });

    this.cache.set(cacheKey, data);
    return data;
  }

  /**
   * Decodes an ArrayBuffer via the audio context and computes its waveform peaks.
   */
  public async analyzeArrayBuffer(
    assetId: string,
    arrayBuffer: ArrayBuffer,
    context: any,
    options?: AnalyzeWaveformOptions
  ): Promise<WaveformData> {
    const resolution = options?.resolution ?? 512;
    const version = options?.version ?? "1.0";
    const cacheKey = computeWaveformCacheKey(assetId, resolution, version);

    if (!options?.bypassCache) {
      const cached = this.cache.get(cacheKey);
      if (cached) {
        return cached;
      }
    }

    const decoded = await context.decodeAudioData(arrayBuffer);
    return this.analyzeAudioBuffer(assetId, decoded, options);
  }

  public getCached(assetId: string, resolution = 512, version = "1.0"): WaveformData | undefined {
    return this.cache.get(computeWaveformCacheKey(assetId, resolution, version));
  }

  public clearCache(): void {
    this.cache.clear();
  }

  public getCacheSize(): number {
    return this.cache.size();
  }
}
