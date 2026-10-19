import { useEffect, useRef, useState } from "react";

interface Props {
  before: HTMLCanvasElement;
  after: HTMLCanvasElement;
  mode: "slider" | "split";
}

function Mirror({ source, className, style }: { source: HTMLCanvasElement; className?: string; style?: React.CSSProperties }) {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const c = ref.current;
    if (!c) return;
    c.width = source.width;
    c.height = source.height;
    c.getContext("2d")!.drawImage(source, 0, 0);
  }, [source]);
  return <canvas ref={ref} className={className} style={style} />;
}

export function CompareView({ before, after, mode }: Props) {
  const [pos, setPos] = useState(50);
  const box = useRef<HTMLDivElement>(null);
  const dragging = useRef(false);

  const move = (clientX: number) => {
    const r = box.current?.getBoundingClientRect();
    if (!r) return;
    setPos(Math.max(0, Math.min(100, ((clientX - r.left) / r.width) * 100)));
  };

  if (mode === "split") {
    return (
      <div className="grid h-full w-full grid-cols-1 items-center gap-3 sm:grid-cols-2">
        {[{ c: before, l: "Before" }, { c: after, l: "After" }].map(({ c, l }) => (
          <figure key={l} className="relative">
            <Mirror source={c} className="mx-auto block max-h-[70vh] w-auto max-w-full rounded-md" />
            <figcaption className="absolute left-2 top-2 rounded bg-background/70 px-2 py-0.5 text-xs">{l}</figcaption>
          </figure>
        ))}
      </div>
    );
  }

  return (
    <div
      ref={box}
      className="relative mx-auto max-h-[72vh] w-fit max-w-full touch-none select-none overflow-hidden rounded-md"
      onPointerDown={(e) => {
        dragging.current = true;
        (e.target as Element).setPointerCapture?.(e.pointerId);
        move(e.clientX);
      }}
      onPointerMove={(e) => dragging.current && move(e.clientX)}
      onPointerUp={() => (dragging.current = false)}
      onPointerCancel={() => (dragging.current = false)}
    >
      <Mirror source={before} className="block max-h-[72vh] w-auto max-w-full" />
      <Mirror
        source={after}
        className="absolute inset-0 h-full w-full"
        style={{ clipPath: `inset(0 0 0 ${pos}%)` }}
      />
      <div className="pointer-events-none absolute inset-y-0 w-0.5 bg-primary" style={{ left: `${pos}%` }}>
        <div className="absolute left-1/2 top-1/2 flex h-9 w-9 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-lg">
          ⟷
        </div>
      </div>
      <span className="pointer-events-none absolute left-2 top-2 rounded bg-background/70 px-2 py-0.5 text-xs">Before</span>
      <span className="pointer-events-none absolute right-2 top-2 rounded bg-background/70 px-2 py-0.5 text-xs">After</span>
      <input
        type="range"
        min={0}
        max={100}
        value={pos}
        onChange={(e) => setPos(Number(e.target.value))}
        aria-label="Before and after divider"
        className="sr-only"
      />
    </div>
  );
}
