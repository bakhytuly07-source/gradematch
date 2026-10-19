# GradeMatch frontend

React/TypeScript with Vite and Vitest. See the repository [setup guide](../README.md)
for prerequisites, ports, API/mock selection, tests and build commands, and the
[release checklist](../_docs/release-checks.md) for verified and pending evidence.
All backend calls go through `src/services/`; mock and real adapters share one
interface. The mock is synthetic and stores accounts/looks in memory only.
