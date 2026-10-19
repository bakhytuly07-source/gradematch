import { createFileRoute } from "@tanstack/react-router";
import { AuthForm } from "@/components/AuthForm";

export const Route = createFileRoute("/register")({
  validateSearch: (s: Record<string, unknown>) => ({ redirect: typeof s.redirect === "string" ? s.redirect : undefined }),
  head: () => ({
    meta: [
      { title: "Create account — GradeMatch" },
      { name: "description", content: "Create a free GradeMatch account to save your color looks." },
      { property: "og:title", content: "Create account — GradeMatch" },
      { property: "og:description", content: "Create a free GradeMatch account to save your color looks." },
    ],
  }),
  component: () => <AuthForm mode="register" redirect={Route.useSearch().redirect} />,
});
