import { toast } from "sonner";
import { Link, useNavigate } from "@tanstack/react-router";
import { service, useMe } from "@/services";
import { Button } from "@/components/ui/button";

export function SiteHeader() {
  const me = useMe();
  const navigate = useNavigate();
  return (
    <header className="flex items-center justify-between gap-4 px-4 py-4 sm:px-8">
      <Link to="/" className="flex items-center gap-2">
        <span className="h-3 w-3 rounded-full bg-primary" aria-hidden />
        <span className="font-display text-2xl">GradeMatch</span>
      </Link>
      <nav className="flex items-center gap-1 text-sm sm:gap-2">
        <Button asChild variant="ghost" size="sm">
          <Link to="/" activeOptions={{ exact: true }} activeProps={{ className: "text-primary" }}>Studio</Link>
        </Button>
        <Button asChild variant="ghost" size="sm">
          <Link to="/library" activeProps={{ className: "text-primary" }}>Library</Link>
        </Button>
        {me ? (
          <Button
            variant="outline"
            size="sm"
            onClick={async () => {
              try { await service.logout(); }
              catch (e) { toast.error((e as Error).message); }
              finally { navigate({ to: "/", replace: true }); }
            }}
          >
            Log out
          </Button>
        ) : (
          <Button asChild size="sm">
            <Link to="/login">Log in</Link>
          </Button>
        )}
      </nav>
    </header>
  );
}
