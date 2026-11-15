#!/usr/bin/env bash
set -euo pipefail
gh label create devops --color 0052CC 2>/dev/null || true
gh api repos/:owner/:repo/milestones -f title="M10 Environments" >/dev/null 2>&1 || true
mk() { gh issue create --label devops --milestone "M10 Environments" --title "$1" --body "Goal: $2

Description: $3"; }
mk "Separate dev and production environments" "Dev and production are two independent services with their own databases." "gradematch-web stays as dev. Add gradematch-prod (free, Docker, auto-deploy off) to render.yaml with its own database in Neon and DEPLOYMENT_ENVIRONMENT set per environment."
mk "Dev deploys only after CI passes" "A broken commit never reaches dev." "Set the dev service to deploy after CI checks pass and show the evidence."
mk "Manual promotion workflow dev to production" "A person promotes exactly the version running in dev to production with one manual action." "A workflow_dispatch workflow with a confirmation input and a production environment reads the live commit of dev, checks CI and health, deploys that commit to prod through the deploy hook, waits for health, smoke-tests and tags the release."
mk "Environment and version in telemetry for dev and prod" "The dashboard can tell dev and prod, and each version, apart." "Both environments report DEPLOYMENT_ENVIRONMENT and APP_VERSION; a local demo runs a dev and a prod instance against the observability stack and the Grafana filters show both."
mk "Environments and promotion documentation and evidence" "A reader understands the environments and can see a real promotion." "docs/environments.md, README section, screenshots of both services, a successful promotion run and a rejected run."
