import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { service, useMe, type Look } from "@/services";
import { downloadBlob } from "@/lib/apply-lut";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/library")({
  head: () => ({
    meta: [
      { title: "Your Library — GradeMatch" },
      { name: "description", content: "Your saved GradeMatch color looks." },
      { property: "og:title", content: "Your Library — GradeMatch" },
      { property: "og:description", content: "Your saved GradeMatch color looks." },
    ],
  }),
  component: Library,
});

function Library() {
  const me = useMe();
  const navigate = useNavigate();
  const [looks, setLooks] = useState<Look[] | null>(null);
  const [editing, setEditing] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [owner, setOwner] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [reload, setReload] = useState(0);
  const currentUser = useRef(me?.id);
  currentUser.current = me?.id;
  const mutating = useRef(new Set<string>());

  useEffect(() => {
    setLooks(null);
    setOwner(null);
    setLoadError(null);
    setEditing(null);
    if (me === undefined) return;
    if (!me) {
      navigate({ to: "/login", search: { redirect: "/library" }, replace: true });
      return;
    }
    let live = true;
    service.listLooks().then(ls => {if (live) {setLooks(ls); setOwner(me.id);}}).catch((e) => {if (live) setLoadError(e.message);});
    return () => {live = false;};
  }, [me, navigate, reload]);

  const replace = (l: Look) => setLooks((ls) => ls?.map((x) => (x.id === l.id ? l : x)) ?? null);

  async function mutate(id: string, action: () => Promise<void>) {
    const key = `${me?.id}:${id}`;
    if (mutating.current.has(key)) return;
    mutating.current.add(key);
    try { await action(); }
    catch (e) { if (currentUser.current === me?.id) toast.error((e as Error).message); }
    finally { mutating.current.delete(key); }
  }
  async function rename(id: string) {
    await mutate(id, async () => {
      const look = await service.renameLook(id, draft.trim());
      if (currentUser.current !== me?.id) return;
      replace(look); setEditing(null);
    });
  }

  return (
    <main className="px-4 pb-16 sm:px-8">
      <h1 className="text-4xl sm:text-5xl">Your looks</h1>
      <p className="mt-2 text-muted-foreground">Open a look to use it on a new photo.</p>
      {!me ? <p className="mt-8">{me === undefined ? "Restoring session…" : "Log in to view your Library."}</p> : loadError ? <div className="mt-8"><p role="alert">{loadError}</p><Button onClick={() => setReload(n => n + 1)}>Retry</Button></div> : !looks || owner !== me.id ? (
        <div className="mt-8 grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-4">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="aspect-[4/3] animate-pulse rounded-lg bg-muted" />
          ))}
        </div>
      ) : looks.length === 0 ? (
        <div className="mt-12 rounded-xl border border-dashed p-10 text-center">
          <p className="text-lg">No saved looks yet.</p>
          <Button asChild className="mt-4">
            <Link to="/">Make your first look</Link>
          </Button>
        </div>
      ) : (
        <div className="mt-8 grid grid-cols-1 gap-5 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-4">
          {[...looks].sort((a, b) => Number(b.favorite) - Number(a.favorite)).map((l) => (
            <article key={l.id} className="overflow-hidden rounded-lg bg-card">
              <Link to="/" search={{ look: l.id }} className="block">
                <img src={l.thumbnail || undefined} alt={l.name} className="aspect-[4/3] w-full bg-stage object-cover" />
              </Link>
              <div className="space-y-3 p-3">
                <div className="flex items-center gap-2">
                  {editing === l.id ? (
                    <Input autoFocus value={draft} onChange={(e) => setDraft(e.target.value)} onKeyDown={(e) => e.key === "Enter" && rename(l.id)} onBlur={() => rename(l.id)} className="h-9" />
                  ) : (
                    <button className="flex-1 truncate text-left font-medium" title="Rename" onClick={() => { setEditing(l.id); setDraft(l.name); }}>
                      {l.name}
                    </button>
                  )}
                  <button
                    aria-label={l.favorite ? "Remove from favorites" : "Add to favorites"}
                    onClick={() => mutate(l.id, async () => {const look = await service.toggleFavorite(l.id); if (currentUser.current === me?.id) replace(look);})}
                    className={cn("text-xl", l.favorite ? "text-primary" : "text-muted-foreground hover:text-foreground")}
                  >
                    {l.favorite ? "★" : "☆"}
                  </button>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button asChild size="sm"><Link to="/" search={{ look: l.id }}>Open</Link></Button>
                  <Button size="sm" variant="secondary" onClick={() => mutate(l.id, async () => {const blob = await service.downloadLutCube(l.styleParams, l.adjustments); if (currentUser.current === me?.id) downloadBlob(blob, `${l.name}.cube`);})}>.cube</Button>
                  <Button size="sm" variant="ghost" onClick={() => { setEditing(l.id); setDraft(l.name); }}>Rename</Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    className="text-destructive"
                    onClick={() => mutate(l.id, async () => {
                      if (!confirm(`Delete "${l.name}"?`)) return;
                      await service.deleteLook(l.id);
                      if (currentUser.current === me?.id) setLooks((ls) => ls?.filter((x) => x.id !== l.id) ?? null);
                    })}
                  >
                    Delete
                  </Button>
                </div>
              </div>
            </article>
          ))}
        </div>
      )}
    </main>
  );
}
