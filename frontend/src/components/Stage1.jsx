import { useState, useRef, useEffect } from 'react';
import MarkdownRenderer from './MarkdownRenderer';
import './Stage1.css';

export default function Stage1({ responses, streaming }) {
  const [activeTab, setActiveTab] = useState(0);
  const thinkingRef = useRef(null);
  const userScrolledRef = useRef(false);

  // Get models from either completed responses or streaming state
  const models = responses?.length > 0 
    ? responses.map(r => r.model)
    : streaming ? Object.keys(streaming) : [];

  if (models.length === 0) {
    return null;
  }

  const currentModel = models[activeTab];
  const completedResponse = responses?.find(r => r.model === currentModel);
  const streamingData = streaming?.[currentModel];
  
  // Use completed response if available, otherwise show streaming content
  const displayContent = completedResponse?.response || streamingData?.content || '';
  const thinkingContent = streamingData?.thinking || '';
  const isStreaming = streamingData?.isStreaming && !completedResponse;
  const tokensPerSecond = streamingData?.tokensPerSecond;
  const thinkingSeconds = streamingData?.thinkingSeconds;
  const elapsedSeconds = streamingData?.elapsedSeconds;

  // Auto-scroll thinking content while streaming (unless user scrolled up)
  useEffect(() => {
    if (thinkingRef.current && isStreaming && thinkingContent && !userScrolledRef.current) {
      thinkingRef.current.scrollTop = thinkingRef.current.scrollHeight;
    }
  }, [thinkingContent, isStreaming]);

  // Reset user scroll flag when streaming stops or model changes
  useEffect(() => {
    userScrolledRef.current = false;
  }, [currentModel, isStreaming]);

  // Handle scroll in thinking content
  const handleThinkingScroll = (e) => {
    const el = e.target;
    const isAtBottom = el.scrollHeight - el.scrollTop <= el.clientHeight + 20;
    if (!isAtBottom) {
      userScrolledRef.current = true;
    } else {
      userScrolledRef.current = false;
    }
  };

  // Format timing as "thinking/total"
  const formatTiming = (thinking, elapsed) => {
    if (elapsed === undefined) return null;
    const t = thinking !== undefined ? thinking : elapsed;
    return `${t}s/${elapsed}s`;
  };

  return (
    <div className="stage stage1">
      <h3 className="stage-title">Stage 1: Individual Responses</h3>

      {models.length > 0 && (
        <>
          <div className="tabs">
            {models.map((model, index) => {
              const modelStreaming = streaming?.[model];
              const modelComplete = responses?.find(r => r.model === model);
              const hasContent = modelComplete || modelStreaming?.content;
              const modelTps = modelStreaming?.tokensPerSecond;
              const modelTiming = modelStreaming?.elapsedSeconds !== undefined 
                ? `${modelStreaming?.thinkingSeconds ?? modelStreaming?.elapsedSeconds}s/${modelStreaming?.elapsedSeconds}s`
                : null;
              
              return (
                <button
                  key={index}
                  className={`tab ${activeTab === index ? 'active' : ''} ${modelStreaming?.isStreaming && !modelComplete ? 'streaming' : ''}`}
                  onClick={() => setActiveTab(index)}
                >
                  {model.split('/')[1] || model}
                  {modelStreaming?.isStreaming && !modelComplete && modelTiming && <span className="timing-indicator">{modelTiming}</span>}
                  {modelStreaming?.isStreaming && !modelComplete && <span className="streaming-indicator">●</span>}
                </button>
              );
            })}
          </div>

          <div className="tab-content">
            <div className="model-name">
              {currentModel}
              {tokensPerSecond !== undefined && <span className="tps-badge">{tokensPerSecond.toFixed(1)} tok/s</span>}
              {formatTiming(thinkingSeconds, elapsedSeconds) && <span className="timing-badge">{formatTiming(thinkingSeconds, elapsedSeconds)}</span>}
              {isStreaming && <span className="streaming-badge">Streaming...</span>}
            </div>
            
            {thinkingContent && (
              <details className="thinking-section" open={isStreaming}>
                <summary>Thinking</summary>
                <div 
                  className="thinking-content"
                  ref={thinkingRef}
                  onScroll={handleThinkingScroll}
                >
                  {thinkingContent}
                </div>
              </details>
            )}
            
            <div className="response-text markdown-content">
              <MarkdownRenderer>{displayContent}</MarkdownRenderer>
              {isStreaming && <span className="cursor-blink">▌</span>}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
