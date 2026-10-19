import { useRef, useState } from "react";
import { validateImageFile } from "@/services";
import { cn } from "@/lib/utils";

interface Props {
  label: string;
  hint?: string;
  previewUrl?: string | null;
  onFile: (file: File) => void;
  onError: (msg: string) => void;
}

export function DropZone({ label, hint, previewUrl, onFile, onError }: Props) {
  const input = useRef<HTMLInputElement>(null);
  const [over, setOver] = useState(false);

  const take = (f?: File | null) => {
    const err = validateImageFile(f);
    if (err) onError(err);
    else if (f) onFile(f);
  };

  return (
    <button
      type="button"
      onClick={() => input.current?.click()}
      onDragOver={(e) => {
        e.preventDefault();
        setOver(true);
      }}
      onDragLeave={() => setOver(false)}
      onDrop={(e) => {
        e.preventDefault();
        setOver(false);
        take(e.dataTransfer.files?.[0]);
      }}
      className={cn(
        "group relative flex min-h-36 w-full flex-col items-center justify-center overflow-hidden rounded-lg border-2 border-dashed border-border bg-muted/40 p-4 text-center transition-colors hover:border-primary/60",
        over && "border-primary bg-primary/10",
      )}
    >
      {previewUrl ? (
        <>
          <img src={previewUrl} alt="" className="absolute inset-0 h-full w-full object-cover opacity-80" />
          <span className="relative rounded bg-background/80 px-2 py-1 text-xs">Click or drop to replace</span>
        </>
      ) : (
        <>
          <span className="font-medium">{label}</span>
          <span className="mt-1 text-sm text-muted-foreground">{hint ?? "Drag a photo here or click to choose · JPG, PNG, WebP up to 15 MB"}</span>
        </>
      )}
      <input
        ref={input}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        className="hidden"
        onChange={(e) => {
          take(e.target.files?.[0]);
          e.target.value = "";
        }}
      />
    </button>
  );
}
