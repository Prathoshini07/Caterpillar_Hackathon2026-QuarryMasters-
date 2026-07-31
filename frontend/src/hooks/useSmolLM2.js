/**
 * useSmolLM2.js
 * Runs SmolLM2-135M-Instruct fully in-browser via @huggingface/transformers (WASM).
 * Uses browser Cache API to cache model weights locally after initial download.
 */
import { useState, useCallback, useRef } from 'react';

let pipelineInstance = null;
let pipelineLoading = false;
const listeners = [];

async function getPipeline() {
  if (pipelineInstance) return pipelineInstance;
  if (pipelineLoading) {
    return new Promise((resolve) => listeners.push(resolve));
  }
  pipelineLoading = true;
  try {
    const { pipeline, env } = await import('@huggingface/transformers');
    // Enable browser cache API so weights are stored permanently in browser storage
    env.allowLocalModels = false;
    env.useBrowserCache = true;

    pipelineInstance = await pipeline(
      'text-generation',
      'HuggingFaceTB/SmolLM2-135M-Instruct',
      { dtype: 'q4', device: 'wasm' }
    );
    listeners.forEach((r) => r(pipelineInstance));
    listeners.length = 0;
    return pipelineInstance;
  } finally {
    pipelineLoading = false;
  }
}

/**
 * @returns {{ generate, summary, loading, error, modelLoading, cancel }}
 */
export function useSmolLM2() {
  const [summary, setSummary] = useState('');
  const [loading, setLoading] = useState(false);
  const [modelLoading, setModelLoading] = useState(false);
  const [error, setError] = useState('');
  const abortRef = useRef(false);

  const generate = useCallback(async (prompt) => {
    setError('');
    setSummary('');
    abortRef.current = false;

    try {
      if (!pipelineInstance) {
        setModelLoading(true);
      }
      const gen = await getPipeline();
      setModelLoading(false);
      setLoading(true);

      const messages = [
        {
          role: 'system',
          content:
            'You are a concise equipment-rental analyst. Write a short (3–5 sentence) plain-English summary ' +
            'of the rental data below. Highlight key metrics, any anomalies, and one actionable recommendation. ' +
            'Do not use bullet points or markdown. Be direct and professional.',
        },
        { role: 'user', content: prompt },
      ];

      const out = await gen(messages, {
        max_new_tokens: 160,
        temperature: 0.5,
        do_sample: true,
      });

      if (!abortRef.current) {
        const text =
          out?.[0]?.generated_text?.at(-1)?.content?.trim() ||
          out?.[0]?.generated_text?.trim() ||
          '';
        setSummary(text);
      }
    } catch (err) {
      setError(err?.message || 'SmolLM2 failed to generate summary.');
    } finally {
      setLoading(false);
      setModelLoading(false);
    }
  }, []);

  const cancel = useCallback(() => {
    abortRef.current = true;
    setLoading(false);
  }, []);

  return { generate, summary, loading, modelLoading, error, cancel };
}
