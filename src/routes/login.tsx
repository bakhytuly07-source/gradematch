import { createFileRoute } from "@tanstack/react-router";
import { AuthForm } from "@/components/AuthForm";

export const Route = createFileRoute("/login")({
  validateSearch: (s: Record<string, unknown>): { redirect?: string | undefined } => ({ redirect: typeof s["redirect"] === "string" ? s["redirect"] : undefined }),
  head: () => ({
    meta: [
      { title: "Log in — GradeMatch" },
      { name: "description", content: "Log in to GradeMatch to see your saved color looks." },
      { property: "og:title", content: "Log in — GradeMatch" },
      { property: "og:description", content: "Log in to GradeMatch to see your saved color looks." },
    ],
  }),
  component: () => <AuthForm mode="login" redirect={Route.useSearch().redirect} />,
});
