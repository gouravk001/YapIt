import { useEffect, useRef, useState } from "react";

export default function WaveformBars({ analyser }) {
  const rafRef = useRef(null);
  const [levels, setLevels] = useState(() => Array(20).fill(4));

  useEffect(() => {
    if (!analyser) return;
    const data = new Uint8Array(analyser.frequencyBinCount);
    const BAR_COUNT = 20;

    const tick = () => {
      analyser.getByteFrequencyData(data);
      const step = Math.floor(data.length / BAR_COUNT);
      setLevels(
        Array.from({ length: BAR_COUNT }, (_, i) => {
          const avg =
            data.slice(i * step, (i + 1) * step).reduce((a, b) => a + b, 0) / step;
          return Math.max(4, (avg / 255) * 64);
        })
      );
      rafRef.current = requestAnimationFrame(tick);
    };

    rafRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(rafRef.current);
  }, [analyser]);

  return (
    <div className="flex items-center justify-center gap-1.5 h-16" aria-label="Audio waveform">
      {levels.map((h, i) => (
        <div
          key={i}
          className="w-1.5 rounded-full bg-gradient-to-t from-red-500 to-rose-300 transition-[height] duration-75"
          style={{ height: `${h}px` }}
        />
      ))}
    </div>
  );
}

