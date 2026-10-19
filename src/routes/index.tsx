import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { DropZone } from "@/components/DropZone";
import { CompareView } from "@/components/CompareView";
import { DEFAULT_ADJUSTMENTS, service, useMe, type Adjustments, type LutData, type StyleParams } from "@/services";
import { downloadBlob, loadImage, renderToCanvas } from "@/lib/apply-lut";
import { cn } from "@/lib/utils";
import lake from "@/assets/sample-lake.jpg";
import portrait from "@/assets/sample-portrait.jpg";
import cafe from "@/assets/sample-cafe.jpg";

const SAMPLES = [
  { src: lake, name: "Lake" },
  { src: portrait, name: "Portrait" },
  { src: cafe, name: "Café" },
];

const SLIDERS: { key: keyof Adjustments; label: string; min: number; max: number; help: string }[] = [
  { key: "intensity", label: "Look intensity", min: 0, max: 100, help: "How strongly the style shows" },
  { key: "contrast", label: "Contrast", min: -50, max: 50, help: "Softer or punchier" },
  { key: "saturation", label: "Saturation", min: -50, max: 50, help: "Muted or vivid colors" },
  { key: "warmth", label: "Warmth", min: -50, max: 50, help: "Cooler blue or warmer gold" },
];

// Keeps studio work alive while visiting other pages (in-memory only).
const cache: {
  refUrl?: string | null;
  refFile?: File | null;
  style?: StyleParams | null;
  targetUrl?: string | null;
  adj?: Adjustments;
} = {};

export const Route = createFileRoute("/")({
  validateSearch: (s: Record<string, unknown>) => ({ look: typeof s.look === "string" ? s.look : undefined }),
  head: () => ({
    meta: [
      { title: "GradeMatch — Copy the colors of a photo you love" },
      { name: "description", content: "Upload a photo you love, copy its color style onto your own photo, and download a LUT." },
      { property: "og:title", content: "GradeMatch — Copy the colors of a photo you love" },
      { property: "og:description", content: "Upload a photo you love, copy its color style onto your own photo, and download a LUT." },
    ],
  }),
  component: Studio,
});

function Studio() {
  const { look: lookId } = Route.useSearch();
  const navigate = useNavigate();
  const me = useMe();

  const [refFile, setRefFile] = useState<File | null>(cache.refFile ?? null);
  const [refUrl, setRefUrl] = useState<string | null>(cache.refUrl ?? null);
  const [refError, setRefError] = useState<string | null>(null);
  const [generating, setGenerating] = useState(false);
  const [progress, setProgress] = useState(0);
  const [style, setStyle] = useState<StyleParams | null>(cache.style ?? null);

  const [targetUrl, setTargetUrl] = useState<string | null>(cache.targetUrl ?? null);
  const [targetError, setTargetError] = useState<string | null>(null);
  const [img, setImg] = useState<HTMLImageElement | null>(null);

  const [adj, setAdj] = useState<Adjustments>(cache.adj ?? DEFAULT_ADJUSTMENTS);
  const [debAdj, setDebAdj] = useState(adj);
  const [lut, setLut] = useState<LutData | null>(null);
  const [mode, setMode] = useState<"slider" | "split">("slider");
  const [saveOpen, setSaveOpen] = useState(false);
  const [saveName, setSaveName] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    Object.assign(cache, { refFile, refUrl, style, targetUrl, adj });
  }, [refFile, refUrl, style, targetUrl, adj]);

  // Load a saved look from the library
  useEffect(() => {
    if (!lookId || me === undefined) return;
    if (!me) {
      navigate({ to: "/login", search: { redirect: `/?look=${lookId}` } });
      return;
    }
    service
      .getLook(lookId)
      .then((l) => {
        setStyle(l.styleParams);
        setAdj(l.adjustments);
        setDebAdj(l.adjustments);
        setRefUrl(l.thumbnail);
        setRefFile(null);
        toast.success(`"${l.name}" loaded — pick a photo to apply it to.`);
      })
      .catch((e) => toast.error(e.message));
  }, [lookId, me, navigate]);

  // Debounce slider changes by 150ms
  useEffect(() => {
    const t = setTimeout(() => setDebAdj(adj), 150);
    return () => clearTimeout(t);
  }, [adj]);

  useEffect(() => {
    if (!style) return setLut(null);
    let live = true;
    service.renderLut(style, debAdj).then((l) => live && setLut(l));
    return () => {
      live = false;
    };
  }, [style, debAdj]);

  useEffect(() => {
    if (!targetUrl) return setImg(null);
    loadImage(targetUrl).then(setImg).catch((e) => setTargetError(e.message));
  }, [targetUrl]);

  const before = useMemo(() => (img ? renderToCanvas(img, null) : null), [img]);
  const after = useMemo(() => (img ? renderToCanvas(img, lut) : null), [img, lut]);

  async function generate() {
    if (!refFile) return;
    setGenerating(true);
    setProgress(5);
    const tick = setInterval(() => setProgress((p) => Math.min(92, p + 8)), 150);
    try {
      const s = await service.generateLook(refFile);
      setStyle(s);
      setProgress(100);
      toast.success("Color style ready. Now pick a photo to apply it to.");
    } catch (e) {
      setRefError((e as Error).message);
    } finally {
      clearInterval(tick);
      setGenerating(false);
    }
  }

  async function downloadImage(type: "png" | "jpeg") {
    if (!img || !lut) return;
    const c = renderToCanvas(img, lut, 6000);
    c.toBlob((b) => b && downloadBlob(b, `gradematch.${type === "png" ? "png" : "jpg"}`), `image/${type}`, 0.92);
  }

  async function downloadCube() {
    if (!style) return;
    downloadBlob(await service.downloadLutCube(style, adj), "gradematch-look.cube");
  }

  function startSave() {
    if (!me) {
      toast("Log in to save looks to your library.", {
        action: { label: "Log in", onClick: () => navigate({ to: "/login", search: { redirect: "/" } }) },
      });
      return;
    }
    setSaveName("");
    setSaveOpen(true);
  }

  async function save() {
    if (!style) return;
    setSaving(true);
    try {
      const source = after ?? null;
      let thumbnail = refUrl ?? "";
      if (source) {
        const t = document.createElement("canvas");
        const s = 480 / Math.max(source.width, source.height);
        t.width = source.width * s;
        t.height = source.height * s;
        t.getContext("2d")!.drawImage(source, 0, 0, t.width, t.height);
        thumbnail = t.toDataURL("image/jpeg", 0.8);
      }
      await service.saveLook({ name: saveName, thumbnail, styleParams: style, adjustments: adj });
      setSaveOpen(false);
      toast.success("Saved to your library.", {
        action: { label: "Open library", onClick: () => navigate({ to: "/library" }) },
      });
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setSaving(false);
    }
  }

  const canExport = !!style;
  const canExportImage = !!style && !!img && !!lut;

  return (
    <main className="grid gap-6 px-4 pb-12 sm:px-8 lg:grid-cols-[minmax(0,1fr)_380px]">
      {/* Preview — the light table */}
      <section className="order-1 flex min-h-[50vh] flex-col rounded-xl bg-stage p-3 sm:p-5 lg:min-h-[78vh]">
        <div className="mb-3 flex items-center justify-between gap-2">
          <p className="text-sm text-muted-foreground">{style ? "Preview" : "Your preview appears here"}</p>
          <div className="flex rounded-lg bg-secondary p-1 text-sm">
            {(["slider", "split"] as const).map((m) => (
              <button
                key={m}
                onClick={() => setMode(m)}
                className={cn("rounded-md px-3 py-1.5 transition-colors", mode === m ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground")}
              >
                {m === "slider" ? "Before / after" : "Side by side"}
              </button>
            ))}
          </div>
        </div>
        <div className="flex flex-1 items-center justify-center">
          {before && after ? (
            <CompareView before={before} after={after} mode={mode} />
          ) : (
            <div className="max-w-sm text-center">
              <h1 className="text-4xl sm:text-5xl">Copy the colors of a photo you love.</h1>
              <p className="mt-4 text-muted-foreground">
                Add a reference photo, then a photo of your own. We'll match the look — you fine‑tune it.
              </p>
            </div>
          )}
        </div>
      </section>

      {/* Controls */}
      <aside className="order-2 space-y-8">
        <Step n={1} title="Photo you love">
          <DropZone
            label="Add a reference photo"
            previewUrl={refUrl}
            onFile={(f) => {
              setRefError(null);
              setRefFile(f);
              setRefUrl(URL.createObjectURL(f));
              setStyle(null);
            }}
            onError={setRefError}
          />
          {refError && <p className="text-sm text-destructive">{refError}</p>}
          <Button size="lg" className="w-full" disabled={!refFile || generating} onClick={generate}>
            {generating ? `Reading colors… ${progress}%` : style ? "Generate again" : "Generate Color Style"}
          </Button>
          {generating && (
            <div className="h-1 overflow-hidden rounded bg-secondary">
              <div className="h-full bg-primary transition-all" style={{ width: `${progress}%` }} />
            </div>
          )}
        </Step>

        <Step n={2} title="Your photo">
          <DropZone
            label="Add your photo"
            previewUrl={null}
            hint="Drag a photo here or click · or try a sample below"
            onFile={(f) => {
              setTargetError(null);
              setTargetUrl(URL.createObjectURL(f));
            }}
            onError={setTargetError}
          />
          {targetError && <p className="text-sm text-destructive">{targetError}</p>}
          <div className="grid grid-cols-3 gap-2">
            {SAMPLES.map((s) => (
              <button
                key={s.name}
                onClick={() => {
                  setTargetError(null);
                  setTargetUrl(s.src);
                }}
                className={cn("overflow-hidden rounded-md ring-2 ring-transparent transition", targetUrl === s.src && "ring-primary")}
              >
                <img src={s.src} alt={`${s.name} sample`} loading="lazy" className="aspect-square w-full object-cover" />
              </button>
            ))}
          </div>
        </Step>

        <Step
          n={3}
          title="Fine-tune"
          action={
            <Button variant="ghost" size="sm" onClick={() => setAdj(DEFAULT_ADJUSTMENTS)}>
              Reset
            </Button>
          }
        >
          <div className={cn("space-y-6", !style && "pointer-events-none opacity-40")}>
            {SLIDERS.map((s) => (
              <div key={s.key} className="space-y-3">
                <div className="flex items-baseline justify-between">
                  <span className="font-medium">{s.label}</span>
                  <span className="text-sm tabular-nums text-muted-foreground">{adj[s.key]}</span>
                </div>
                <Slider
                  min={s.min}
                  max={s.max}
                  step={1}
                  value={[adj[s.key]]}
                  onValueChange={([v]) => setAdj((a) => ({ ...a, [s.key]: v }))}
                  aria-label={s.label}
                />
                <p className="text-xs text-muted-foreground">{s.help}</p>
              </div>
            ))}
          </div>
        </Step>

        <Step n={4} title="Take it with you">
          <div className="grid gap-2">
            <Button variant="secondary" disabled={!canExport} onClick={downloadCube}>
              Download LUT (.cube)
            </Button>
            <div className="grid grid-cols-2 gap-2">
              <Button variant="secondary" disabled={!canExportImage} onClick={() => downloadImage("png")}>
                Download image (PNG)
              </Button>
              <Button variant="secondary" disabled={!canExportImage} onClick={() => downloadImage("jpeg")}>
                Download image (JPEG)
              </Button>
            </div>
            <Button variant="outline" disabled={!canExport} onClick={startSave}>
              ☆ Save to Library
            </Button>
          </div>
        </Step>
      </aside>

      <Dialog open={saveOpen} onOpenChange={setSaveOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Name this look</DialogTitle>
          </DialogHeader>
          <Input autoFocus placeholder="e.g. Golden hour" value={saveName} onChange={(e) => setSaveName(e.target.value)} onKeyDown={(e) => e.key === "Enter" && save()} />
          <DialogFooter>
            <Button onClick={save} disabled={saving}>
              {saving ? "Saving…" : "Save"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </main>
  );
}

function Step({ n, title, action, children }: { n: number; title: string; action?: React.ReactNode; children: React.ReactNode }) {
  return (
    <section className="space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="flex items-center gap-3 text-xl">
          <span className="flex h-7 w-7 items-center justify-center rounded-full border border-primary font-sans text-sm text-primary">{n}</span>
          {title}
        </h2>
        {action}
      </div>
      {children}
    </section>
  );
}
