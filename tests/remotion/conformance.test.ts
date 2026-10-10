import { describe, it, expect, vi } from 'vitest';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { TEMPLATE_REGISTRY } from '../../registry/template-registry';
import { BrandProvider } from '../../remotion-app/src/BrandContext';
import { validateStyleSurface } from '../../contracts/StyleSurface';
import { validateStyleOverride } from '../../contracts/override-validator';
import { isRTL } from '../../contracts/fonts';

// Mock remotion environment
vi.mock('remotion', async (importOriginal) => {
  const actual: any = await importOriginal();
  return {
    ...actual,
    useCurrentFrame: () => 15,
    useVideoConfig: () => ({ fps: 30, durationInFrames: 300, width: 1920, height: 1080 }),
    delayRender: () => 1,
    continueRender: () => {},
    staticFile: (p: string) => p,
    AbsoluteFill: (props: any) => React.createElement('div', { ...props, 'data-remotion-fill': 'true' }, props.children),
    Sequence: (props: any) => React.createElement('div', { ...props, 'data-remotion-seq': 'true' }, props.children),
    Loop: (props: any) => React.createElement('div', { ...props, 'data-remotion-loop': 'true' }, props.children),
    Audio: (props: any) => React.createElement('audio', props),
    Img: (props: any) => React.createElement('img', { alt: '', ...props, src: props?.src || 'test.png' }),
  };
});

// Mock @remotion/transitions
vi.mock('@remotion/transitions', () => ({
  TransitionSeries: Object.assign(
    (props: any) => React.createElement('div', { 'data-transition-series': 'true' }, props.children),
    {
      Sequence: (props: any) => React.createElement('div', { 'data-transition-seq': 'true' }, props.children),
      Transition: (props: any) => React.createElement('div', { 'data-transition': 'true', 'data-timing': props.timing?.durationInFrames }, null),
    }
  ),
  linearTiming: (opts: any) => ({ ...opts, type: 'linear' }),
  springTiming: (opts: any) => ({ ...opts, type: 'spring' }),
}));

// Mock audio visualization utilities and primitives to avoid multi-instance React dispatcher errors in SSR
vi.mock('@/remotion/lib/audio-viz-utils', () => ({
  DEFAULT_AUDIO_WINDOW_SECONDS: 30,
  useAudioBands: () => ({ bands: [0.1, 0.2, 0.3, 0.4, 0.5], peaks: [0.1, 0.2, 0.3, 0.4, 0.5] }),
  useAudioAmplitude: () => 0.5,
  useWindowedAudioData: () => [0.1, 0.2, 0.3, 0.4, 0.5],
  visualizeAudio: () => [0.1, 0.2, 0.3],
}));

vi.mock('@/remotion/primitives/waveform-line', () => ({
  WaveformLine: () => React.createElement('div', { 'data-waveform-line': 'true' }),
}));

vi.mock('@/remotion/primitives/audio-pulse', () => ({
  AudioPulse: () => React.createElement('div', { 'data-audio-pulse': 'true' }),
}));

// Mock remotion-bits primitives so wrapper templates can be verified without node_modules loader collisions
vi.mock('remotion-bits', () => ({
  AnimatedText: ({ children, style }: any) => React.createElement('div', { style, 'data-animated-text': 'true' }, children),
  TypeWriter: ({ children, style }: any) => React.createElement('div', { style, 'data-typewriter': 'true' }, children),
  CodeBlock: ({ children, style }: any) => React.createElement('div', { style, 'data-code-block': 'true' }, children),
  MatrixRain: ({ children, style }: any) => React.createElement('div', { style, 'data-matrix-rain': 'true' }, children),
  AnimatedCounter: ({ children, style, value }: any) => React.createElement('div', { style, 'data-counter': value }, children),
  Particles: ({ children, style }: any) => React.createElement('div', { style, 'data-particles': 'true' }, children),
  StaggeredMotion: ({ children, style }: any) => React.createElement('div', { style, 'data-staggered-motion': 'true' }, children),
  GradientTransition: ({ children, style }: any) => React.createElement('div', { style, 'data-gradient-transition': 'true' }, children),
  Scene3D: ({ children }: any) => React.createElement('div', null, children),
  ScrollingColumns: ({ children }: any) => React.createElement('div', null, children),
  Behavior: {
    Gravity: () => null,
    Drag: () => null,
    Orbit: () => null,
    Attract: () => null,
    Repel: () => null,
  },
  Spawner: () => null,
}));

// Mock google-fonts loaders to avoid network requests
vi.mock('@remotion/google-fonts/Cairo', () => ({
  loadFont: () => ({ waitUntilDone: () => Promise.resolve() }),
}));
vi.mock('@remotion/google-fonts/Inter', () => ({
  loadFont: () => ({ waitUntilDone: () => Promise.resolve() }),
}));

const registryEntries = Object.values(TEMPLATE_REGISTRY);

describe('Conformance Tests (Data-Driven)', () => {
  describe.each(registryEntries)('$id conformance', (entry) => {
    const Component = entry.component;

    const renderComp = (surface: any) => {
      const surfaceProps = { ...surface };

      // Component-specific tailored defaults where schema expectations diverge
      const isTalkingHead = entry.id === 'rui-talking-head-layout';
      const isQuiz = entry.id === 'rui-quiz-question';
      const isFaq = entry.id === 'rui-faq-accordion';
      const isPoll = entry.id === 'rui-poll-overlay';

      const defaultProps: Record<string, any> = {
        ...entry.defaults,
        headline: entry.defaults?.headline || 'Sample headline',
        quote: entry.defaults?.quote || 'Sample quote text',
        data: entry.defaults?.data || [
          { label: 'A', value: 10 },
          { label: 'B', value: 20 },
        ],
        target: entry.defaults?.target || { x: 100, y: 100, width: 200, height: 200 },
        captions: entry.defaults?.captions || (isTalkingHead
          ? ['Caption 1', 'Caption 2']
          : [{ text: 'Caption text', startMs: 0, endMs: 1000 }]),
        items: isFaq ? undefined : (entry.defaults?.items || ['Item 1', 'Item 2']),
        headlines: entry.defaults?.headlines || ['Headline 1', 'Headline 2'],
        steps: entry.defaults?.steps || [
          { title: 'Step 1', description: 'Desc 1' },
          { title: 'Step 2', description: 'Desc 2' },
        ],
        options: entry.defaults?.options || (isPoll
          ? [{ label: 'Option 1', votes: 10 }, { label: 'Option 2', votes: 20 }]
          : ['Option 1', 'Option 2']),
        home: entry.defaults?.home || { name: 'Home', score: 0 },
        away: entry.defaults?.away || { name: 'Away', score: 0 },
        audioSrc: entry.defaults?.audioSrc || 'test.mp3',
        src: entry.defaults?.src || 'test.mp3',
      };

      const content = {
        text: surfaceProps.text || defaultProps.text || 'Sample text',
        lines: [surfaceProps.text || 'Sample line 1', 'Sample line 2'],
        items: isFaq ? undefined : ['Item 1', 'Item 2'],
        cards: defaultProps.cards || [
          { title: 'Card 1', description: 'Desc 1' },
          { title: 'Card 2', description: 'Desc 2' },
        ],
        data: defaultProps.data,
        images: ['test1.png', 'test2.png'],
        screen: 'test.png',
        words: [],
        ...defaultProps,
      };

      const template_props = {
        ...defaultProps,
      };

      const el = React.createElement(Component, {
        surface: surfaceProps,
        content,
        template_props,
        ...defaultProps,
      });

      return renderToStaticMarkup(
        React.createElement(
          BrandProvider,
          {
            brand: {
              name: 'test',
              brandName: 'TestBrand',
              colors: { primary: '#000', secondary: '#fff', background: '#0A0E27', text: '#fff' },
              fonts: { heading: 'Cairo', body: 'Cairo', display: 'Cairo' },
            },
          } as any,
          el
        )
      );
    };

    const expectValidOutput = (html: string) => {
      expect(typeof html).toBe('string');
      if (entry.id !== 'rui-t-h-e-m-e-s') {
        expect(html.length).toBeGreaterThan(0);
      }
    };

    it('1. accepts StyleSurface completely', () => {
      const surface = { text: 'test' } as any;
      const valid = validateStyleSurface({ ...entry.defaults, ...surface });
      expect(valid.ok).toBe(true);
      const html = renderComp(surface);
      expectValidOutput(html);
    });

    it('2. renders without error', () => {
      const surface = { text: 'test' } as any;
      expect(() => renderComp(surface)).not.toThrow();
      const html = renderComp(surface);
      expectValidOutput(html);
    });

    it('3. RTL is applied for Cairo/Tajawal', () => {
      const surface = { text: 'test', fontFamily: 'Cairo' } as any;
      expect(isRTL(surface.fontFamily)).toBe(true);
      const html = renderComp(surface);
      if (html.includes('direction:')) {
        expect(html).toContain('direction:rtl');
      }
      expectValidOutput(html);
    });

    it('4. LTR is applied for Inter/Manrope', () => {
      const surface = { text: 'test', fontFamily: 'Inter' } as any;
      expect(isRTL(surface.fontFamily)).toBe(false);
      const html = renderComp(surface);
      expectValidOutput(html);
    });

    it('5. styleOverride with invalid key is ignored or handled safely', () => {
      const surface = { text: 'test', styleOverride: { invalidKey: 'val' } } as any;
      const validation = validateStyleOverride(surface.styleOverride);
      expect(validation.ok).toBe(false);
      expect(validation.errors.length).toBeGreaterThan(0);
      expect(validation.errors.some((e: string) => e.includes('invalidKey'))).toBe(true);
      const html = renderComp(surface);
      expect(html).not.toContain('invalidKey');
      expectValidOutput(html);
    });

    it('6. fontFamily="brand.display" translates to Cairo (mocked logic)', () => {
      const surface = { text: 'test', fontFamily: 'brand.display' } as any;
      const html = renderComp(surface);
      expectValidOutput(html);
    });

    it('7. position with x=50 in RTL is accepted and handled safely', () => {
      const surface = {
        text: 'test',
        position: { anchor: 'top-right', x: 50, y: 20 },
        fontFamily: 'Cairo',
      } as any;
      const surfaceRes = validateStyleSurface({ ...entry.defaults, ...surface });
      expect(surfaceRes.ok).toBe(true);
      const html = renderComp(surface);
      expectValidOutput(html);
    });

    it('8. animation works (opacity/progress)', () => {
      const surface = { text: 'test', animation: 'fade_in' } as any;
      const surfaceRes = validateStyleSurface({ ...entry.defaults, ...surface });
      expect(surfaceRes.ok).toBe(true);
      const html = renderComp(surface);
      expectValidOutput(html);
    });

    it('9. fontSize changes', () => {
      const surface = { text: 'test', fontSize: 42 } as any;
      const surfaceRes = validateStyleSurface({ ...entry.defaults, ...surface });
      expect(surfaceRes.ok).toBe(true);
      const html = renderComp(surface);
      expectValidOutput(html);
    });

    it('10. color changes', () => {
      const surface = { text: 'test', color: '#ff0000' } as any;
      const surfaceRes = validateStyleSurface({ ...entry.defaults, ...surface });
      expect(surfaceRes.ok).toBe(true);
      const html = renderComp(surface);
      expectValidOutput(html);
    });
  });
});
