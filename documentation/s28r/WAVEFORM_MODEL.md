# S28-R07: Waveform Data Model & Peak Extraction Specification

## 1. Overview & Architectural Boundaries

The waveform subsystem provides a pure, framework-neutral data representation and extraction pipeline for audio waveform visualization.

```text
Audio Asset (Raw PCM / AudioBuffer)
                │
                ▼
 contracts/waveform.ts (extractWaveformPeaks)
 [Pure Functional Math - Zero UI/WebAudio/React]
                │
                ▼
 WaveformData (Validated via WaveformDataSchema)
                │
                ▼
 preview/audio/waveform-analyzer.ts (WaveformCache)
 [LRU Cache: Keyed by asset_id, sample_rate, duration, resolution, version]
                │
                ▼
 Timeline UI Visualization (Downstream consumer in future milestones)
```

### Invariants:
1. **Zero UI/DOM/React Dependencies**: Peak extraction algorithms live strictly within `contracts/waveform.ts` and depend only on numeric arrays and pure JavaScript math.
2. **Deterministic Output**: Given identical PCM channel data and resolution, the peak extraction outputs bitwise-identical peak arrays across all invocations.
3. **Bounded Memory**: Raw audio PCM buffers are never stored inside canonical editor state or mutation history. Only compact `WaveformData` structures are cached.

---

## 2. Data Contract Specification

```typescript
export interface WaveformData {
  asset_id: string;
  sample_rate: number;
  duration: number;
  channels: number;
  resolution: number;
  version: number;
  peaks: number[]; // Normalized amplitude values in range [0.0, 1.0]
}
```

Validated by `WaveformDataSchema` via Zod:
- `asset_id`: Non-empty string identifying the canonical asset.
- `sample_rate`: Positive integer (e.g. 44100, 48000).
- `duration`: Positive number in seconds.
- `channels`: Positive integer (1 for mono, 2 for stereo).
- `resolution`: Integer $\ge 1$ defining the number of peak bins.
- `peaks`: Array of numbers $\in [0.0, 1.0]$.
- `version`: Integer tracking the analysis algorithm revision.

---

## 3. Peak Extraction Algorithm

Given $C$ audio channels each containing $N$ samples, and target resolution $R$:

1. **Bin Size Calculation**:
   $$S_{\text{bin}} = \max\left(1, \left\lfloor \frac{N}{R} \right\rfloor\right)$$
2. **Channel Aggregation & Maximum Search**:
   For each bin $b \in [0, R - 1]$:
   $$\text{peak}_b = \max_{c \in [0, C-1]} \left( \max_{i \in [b \cdot S_{\text{bin}}, (b+1) \cdot S_{\text{bin}} - 1]} |x_c[i]| \right)$$
3. **Clamping & Precision**:
   Each peak is clamped to $[0.0, 1.0]$ and rounded to 4 decimal places for deterministic cross-platform consistency and JSON compact serialization.

---

## 4. Bounded Memory & Caching Architecture

### 4.1 Memory Comparison
| Data Representation | 60-Second Audio Clip | Memory Footprint |
| :--- | :--- | :--- |
| **Raw PCM (48kHz, 16-bit stereo)** | 5,760,000 floats | $\approx 23.0 \text{ MB}$ |
| **WaveformData (Resolution: 512)** | 512 numbers | $\approx 4.1 \text{ KB}$ |
| **WaveformData (High-Res: 5168)** | 5,168 numbers | $\approx 41.3 \text{ KB}$ |

### 4.2 Cache Key Formulation
```typescript
computeWaveformCacheKey(asset_id, sample_rate, duration, resolution, version)
```
Generates a deterministic string key:
`wf:${asset_id}:sr_${sample_rate}:dur_${duration.toFixed(3)}:res_${resolution}:v${version}`

### 4.3 WaveformCache (LRU Policy)
- Configurable maximum entries (`maxEntries: 50`) and maximum bytes (`maxMemoryBytes: 10MB`).
- Evicts least-recently-used waveform entries on overflow.
- Guarantees predictable memory ceilings during prolonged editor sessions.
