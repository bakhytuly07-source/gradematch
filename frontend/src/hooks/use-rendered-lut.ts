import { useEffect, useState } from 'react';
import { service, type Adjustments, type GradeMatchService, type LutData, type StyleParams } from '@/services';

/** A result carries the exact immutable settings that produced it. */
export function useRenderedLut(style: StyleParams | null, adjustments: Adjustments,
  api: Pick<GradeMatchService, 'renderLut'> = service) {
  const [result, setResult] = useState<{style: StyleParams; adjustments: Adjustments; lut: LutData} | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    let live = true;
    setError(null);
    if (!style) {setResult(null); return;}
    const timer = setTimeout(() => {
      api.renderLut(style, adjustments).then(lut => {if (live) setResult({style, adjustments, lut});})
        .catch((e: Error) => {if (live) setError(e.message);});
    }, 50);
    return () => {live = false; clearTimeout(timer);};
  }, [style, adjustments, api]);
  const ready = !!result && result.style === style && result.adjustments === adjustments;
  return {result, ready, error};
}
