import { useEffect, useState } from "react";
import { MockService } from "./mock";
import { ApiService } from "./api";
import type { GradeMatchService, User } from "./types";

export * from "./types";
export { validateImageFile } from "./validation";

const apiUrl = import.meta.env["VITE_API_URL"];
const base: GradeMatchService = apiUrl ? new ApiService(apiUrl) : new MockService();

// Tiny auth-change notifier so the UI can react to login/logout.
const listeners = new Set<(u: User | null) => void>();
const emit = async () => {
  const me = await base.getMe();
  listeners.forEach((l) => l(me));
};

export const service: GradeMatchService = {
  ...Object.fromEntries(
    Object.getOwnPropertyNames(Object.getPrototypeOf(base))
      .filter((k) => k !== "constructor")
      .map((k) => [
        k,
        (base as never as Record<string, (...a: unknown[]) => unknown>)[k]!.bind(base),
      ]),
  ),
  register: async (e: string, p: string) => {
    const u = await base.register(e, p);
    await emit();
    return u;
  },
  login: async (e: string, p: string) => {
    const u = await base.login(e, p);
    await emit();
    return u;
  },
  logout: async () => {
    await base.logout();
    await emit();
  },
} as GradeMatchService;

export function useMe() {
  const [me, setMe] = useState<User | null | undefined>(undefined);
  useEffect(() => {
    service.getMe().then(setMe);
    listeners.add(setMe);
    return () => {
      listeners.delete(setMe);
    };
  }, []);
  return me;
}
