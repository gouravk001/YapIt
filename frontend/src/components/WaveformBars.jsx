import { useEffect, useState } from "react";

const BAR_COUNT = 28;
const MIN_HEIGHT = 4;
const MAX_HEIGHT = 48;

export default function WaveformBars({ analyser }) {
  const [levels, setLevels] = useState(() => Array(BAR_COUNT).fill(MIN_HEIGHT));

  useEffect(() => {
    if (!analyser) return;
    const data = new Uint8Array(analyser.frequencyBinCount);
    const step = Math.floor(data.length / BAR_COUNT);
    let frame;

    const tick = () => {
      analyser.getByteFrequencyData(data);
      setLevels(
        Array.from({ length: BAR_COUNT }, (_, i) => {
          const avg = data.slice(i * step, (i + 1) * step).reduce((a, b) => a + b, 0) / step;
          return Math.max(MIN_HEIGHT, (avg / 255) * MAX_HEIGHT);
        }),
      );
      frame = requestAnimationFrame(tick);
    };

    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [analyser]);

  return (
    <div className="flex h-12 items-center justify-center gap-1" aria-hidden="true">
      {levels.map((h, i) => (
        <div
          key={i}
          className="w-1 rounded-full bg-white/80 transition-[height] duration-75"
          style={{ height: `${h}px` }}
        />
      ))}
    </div>
  );
}
