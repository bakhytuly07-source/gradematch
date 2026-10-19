import { useState } from "react";
import { Link, useNavigate } from "@tanstack/react-router";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { service } from "@/services";
import { validateEmail, validatePassword } from "@/services/validation";

export function AuthForm({ mode, redirect }: { mode: "login" | "register"; redirect?: string | undefined }) {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errors, setErrors] = useState<{ email?: string | undefined; password?: string | undefined; form?: string | undefined }>({});
  const [busy, setBusy] = useState(false);
  const isLogin = mode === "login";

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const next = {
      email: validateEmail(email) ?? undefined,
      password: isLogin ? (password ? undefined : "Enter your password.") : (validatePassword(password) ?? undefined),
    };
    setErrors(next);
    if (next.email || next.password) return;
    setBusy(true);
    try {
      if (isLogin) await service.login(email, password);
      else await service.register(email, password);
      navigate({ to: redirect || "/library" });
    } catch (err) {
      setErrors({ form: (err as Error).message });
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto flex max-w-md flex-col px-4 py-16">
      <h1 className="text-4xl">{isLogin ? "Welcome back" : "Create your account"}</h1>
      <p className="mt-2 text-muted-foreground">
        {isLogin ? "Log in to see your saved looks." : "Save looks and use them again anytime."}
      </p>
      <form onSubmit={submit} noValidate className="mt-8 space-y-5">
        <div className="space-y-2">
          <Label htmlFor="email">Email</Label>
          <Input id="email" type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} aria-invalid={!!errors.email} className="h-12" />
          {errors.email && <p className="text-sm text-destructive">{errors.email}</p>}
        </div>
        <div className="space-y-2">
          <Label htmlFor="password">Password</Label>
          <Input id="password" type="password" autoComplete={isLogin ? "current-password" : "new-password"} value={password} onChange={(e) => setPassword(e.target.value)} aria-invalid={!!errors.password} className="h-12" />
          {errors.password ? (
            <p className="text-sm text-destructive">{errors.password}</p>
          ) : (
            !isLogin && <p className="text-sm text-muted-foreground">At least 8 characters.</p>
          )}
        </div>
        {errors.form && <p className="rounded-md bg-destructive/15 p-3 text-sm text-destructive">{errors.form}</p>}
        <Button type="submit" size="lg" className="w-full" disabled={busy}>
          {busy ? "One moment…" : isLogin ? "Log in" : "Create account"}
        </Button>
      </form>
      <p className="mt-6 text-sm text-muted-foreground">
        {isLogin ? "New here? " : "Already have an account? "}
        <Link to={isLogin ? "/register" : "/login"} search={redirect ? { redirect } : {}} className="text-primary underline-offset-4 hover:underline">
          {isLogin ? "Create an account" : "Log in"}
        </Link>
      </p>
    </main>
  );
}
