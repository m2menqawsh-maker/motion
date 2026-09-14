import React from 'react';
import { AbsoluteFill, Sequence } from 'remotion';
import { TEMPLATE_REGISTRY } from '../../registry/template-registry';

class ErrorBoundary extends React.Component<{ children: React.ReactNode, fallback: React.ReactNode }, { hasError: boolean; error: Error | null }> {
  constructor(props: { children: React.ReactNode, fallback: React.ReactNode }) {
    super(props);
    this.state = { hasError: false, error: null };
  }
  static getDerivedStateFromError(error: Error) { return { hasError: true, error }; }
  render() {
    if (this.state.hasError) return this.props.fallback;
    return this.props.children;
  }
}

const DURATION_PER_TEMPLATE = 90; // 3 seconds at 30 fps

export const Showcase: React.FC = () => {
  // Filter out effect templates because @remotion/transitions causes HtmlInCanvas/WebGL crashes when rendering sequentially
  const templates = Object.values(TEMPLATE_REGISTRY).filter(t => t.category !== 'effect');

  // Generic dummy data for templates
  const surface = { text: "عرض القالب", color: "#333", background: "#f0f0f0", animation: { type: "linear" } };
  const content = { text: "هذا النص لتجربة القالب ورؤية الشكل النهائي", images: ["https://picsum.photos/600/600?1", "https://picsum.photos/600/600?2"], lines: ["const code = 'awesome';", "console.log(code);"] };

  return (
    <AbsoluteFill style={{ backgroundColor: 'white', fontFamily: 'Cairo, sans-serif' }}>
      {templates.map((template, index) => {
        const Component = template.component;
        return (
          <Sequence
            key={template.id}
            from={index * DURATION_PER_TEMPLATE}
            durationInFrames={DURATION_PER_TEMPLATE}
            name={template.id}
          >
            <AbsoluteFill style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
                <div style={{ position: 'absolute', top: 100, left: 0, right: 0, textAlign: 'center', fontSize: 60, color: '#333', fontWeight: 'bold', zIndex: 1000, backgroundColor: 'rgba(255,255,255,0.8)', padding: '20px' }}>
                    {template.label.ar || template.label.en}
                </div>
                <div style={{ position: 'absolute', bottom: 100, left: 0, right: 0, textAlign: 'center', fontSize: 40, color: '#666', zIndex: 1000, backgroundColor: 'rgba(255,255,255,0.8)', padding: '10px' }}>
                    قالب رقم ({index + 1} / {templates.length})
                </div>
                
                {/* Scale down the component slightly so it fits well within the frame */}
                <div style={{ position: 'relative', width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <ErrorBoundary fallback={<div style={{ color: 'red', fontSize: 40, textAlign: 'center', padding: 40 }}>فشل تحميل هذا القالب<br/>{template.id}</div>}>
                        <Component 
                            surface={surface}
                            content={content}
                        />
                    </ErrorBoundary>
                </div>
            </AbsoluteFill>
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};

export const getShowcaseDuration = () => {
    const validTemplates = Object.values(TEMPLATE_REGISTRY).filter(t => t.category !== 'effect');
    return Math.max(1, validTemplates.length * DURATION_PER_TEMPLATE);
};
