# Local observability

From the repository root, with Docker Compose v2 installed:

```sh
make obs-up
docker compose -f observability/docker-compose.yaml ps
```

This is the separate `gradematch-observability` project. App `make up/down`
commands and Render are independent. Published ports bind to localhost by default:
Grafana 3000, Prometheus 9090, Loki 3100, Tempo 3200, Collector OTLP HTTP/protobuf
4318 and Collector health 13133. On native Linux, bind OTLP 4318 to the private Docker bridge gateway as
described below, keeping it off public interfaces. Collector Prometheus 8889 and Tempo OTLP
4317/4318 are internal only. This unauthenticated development stack is for local
use; Grafana's initial login is `admin` / `admin` and prompts for a new password.
Open http://localhost:3000 and Connections → Data sources: Prometheus, Loki and
Tempo are provisioned automatically. Select each and use Test (or Save & test).

Wait up to 90 seconds for readiness (Loki may initially return 503):

```sh
for port_path in 13133/ 9090/-/ready 3100/ready 3200/ready 3000/api/health; do
  curl --fail --retry 30 --retry-all-errors --retry-delay 3 "http://localhost:$port_path"
done
# Before changing the initial Grafana password, verify all provisioned sources:
for uid in prometheus loki; do
  curl --fail -u admin:admin "http://localhost:3000/api/datasources/uid/$uid/health"
done
# Tempo uses a frontend Save & test check in Grafana 11.6; test its proxy:
curl --fail -u admin:admin http://localhost:3000/api/datasources/proxy/uid/tempo/ready
```

For a port conflict, run `lsof -nP -iTCP:3000 -sTCP:LISTEN` (replace 3000 with
the conflicting port). Stop the conflicting service or edit the host side of
the corresponding port mapping, then repeat `make obs-up`.

```sh
make obs-down
docker compose -f observability/docker-compose.yaml ps
# Application services remain running:
docker compose ps
make obs-up
```

Named volumes retain metrics, logs, traces and Grafana state across down/up.
Trace blocks expire after 24 hours. To explicitly delete *only observability*
data, run `docker compose -f observability/docker-compose.yaml down -v`.

Configuration references: [Loki native OTLP](https://grafana.com/docs/loki/latest/send-data/otel/),
[Tempo configuration](https://grafana.com/docs/tempo/latest/configuration/).
Application connection and smoke instructions follow below.

For an executable readiness/provisioning assertion, run
`python3 observability/check.py` (set `GRAFANA_PASSWORD` if changed).

## Opt in the app (#131)

No Render variables are required. The default root Compose endpoint is empty,
so ordinary `make up`, `make integration` and `make e2e` do not enable telemetry.
The app's existing #128/#129 instrumentation uses OTLP HTTP/protobuf and appends
`/v1/traces`, `/v1/metrics`, `/v1/logs` to this base URL (see
[backend telemetry](../backend/TELEMETRY.md)). From the repository root:

```sh
make obs-up
python3 observability/check.py
OTEL_EXPORTER_OTLP_ENDPOINT=http://host.docker.internal:4318 docker compose config --quiet
OTEL_EXPORTER_OTLP_ENDPOINT=http://host.docker.internal:4318 docker compose up -d --build --wait app
# To change an already running container, explicitly recreate it:
OTEL_EXPORTER_OTLP_ENDPOINT=http://host.docker.internal:4318 docker compose up -d --force-recreate --wait app
```

The app service passes this variable through, defaults environment to `local`,
and uses the image's default version `dev`. The root Compose `extra_hosts`
entry `host.docker.internal:host-gateway` supplies Linux Docker Engine's mapping
(Docker 20.10+); Docker Desktop supports the same setup. Collector publishes
4318 on the host. On **native Linux** the container cannot reach a host-loopback
listener. Publish OTLP on Docker's private default bridge gateway instead (this
matches `host-gateway`, without exposing OTLP on public host interfaces):

```sh
OBS_OTLP_BIND_ADDRESS=$(docker network inspect bridge --format '{{(index .IPAM.Config 0).Gateway}}') make obs-up
# Repeat this prefix whenever running obs-up on native Linux.
```

Leave the default loopback binding on Docker Desktop. Verify resolution and actual connectivity from the app:

```sh
docker compose exec -T app python -c "import socket,urllib.request; print(socket.gethostbyname('host.docker.internal')); r=urllib.request.urlopen(urllib.request.Request('http://host.docker.internal:4318/v1/traces',data=b'',headers={'Content-Type':'application/x-protobuf'}),timeout=3); print(r.status)"
# Expected: gateway IP, then HTTP 200.
```

### Reproducible smoke

Run `python3 observability/smoke.py` with Python 3.9+ from a clean app/stack or
an existing development database. It uses only the standard library and the
valid checked-in `e2e/fixtures/reference-warm.jpg`. It registers a unique user
(201), retains `access_token` only in process memory, sends the fixture as
multipart `referenceFile` to `/api/generate` (200), and saves the returned JSON
as `styleParams` with neutral adjustments, blank thumbnail and bearer token to
`/api/looks` (201). No secrets or image contents are printed or written. The
saved look follows the existing authenticated save behavior (only parameters
and thumbnail are persisted). Two journeys establish a baseline then measure
an increment even when the metric series did not exist on a fresh stack.
This creates two throwaway users/looks per run; use an expendable local DB.

After a 12-second baseline settling period, the script polls for up to 90
seconds (5-second SDK exports/scrapes plus batching),
asserts all three business counters increment, then finds the scenario generate
request's log trace ID in Loki and verifies that exact trace in Tempo, including
all three resource identity fields. Save sanitized evidence if desired:

```sh
python3 observability/smoke.py | tee /tmp/gradematch-observability-smoke.txt
# Exact standalone Prometheus query (repeat before/after the scenario):
curl --fail --get http://localhost:9090/api/v1/query --data-urlencode 'query=gradematch_styles_generated_total{environment="local",version="dev"}'
# Other counters use gradematch_looks_saved_total and gradematch_users_registered_total.
```

In Grafana Explore select Loki, set an absolute UTC time window covering the
script's scenario timestamps, and run:

```logql
{service_name="gradematch",deployment_environment="local",service_version="dev"} |= "API request completed"
```

Expand a returned log, find its `trace_id` structured metadata and click
**Open trace**. The provisioned derived field opens Tempo with the same ID.
The script prints the generate request ID, an exact nanosecond window and a
Grafana Explore link. API alternatives, replacing START_NS, END_NS and TRACE_ID
with those printed values (these identifiers are safe to record):

```sh
curl --fail --get http://localhost:3100/loki/api/v1/query_range \
  --data-urlencode 'query={service_name="gradematch",deployment_environment="local",service_version="dev"} |= "API request completed"' \
  --data-urlencode 'start=START_NS' --data-urlencode 'end=END_NS' --data-urlencode 'limit=100'
curl --fail http://localhost:3200/api/traces/TRACE_ID
```

For Tempo search, use Explore → Tempo → Search → TraceQL with the same time
window and `{ resource.service.name = "gradematch" && resource.deployment.environment = "local" && resource.service.version = "dev" && name = "POST /api/generate" }`.
The trace returned by ID contains `service.name=gradematch`,
`deployment.environment=local`, `service.version=dev` and the generate span.

### Collector outage and telemetry off

```sh
docker compose -f observability/docker-compose.yaml stop collector
curl --fail -o /dev/null -w '%{http_code}\n' http://localhost:8091/docs
# Expected 200 even when exports fail; queues and HTTP export timeouts are bounded.
docker compose -f observability/docker-compose.yaml start collector
# Explicitly clear endpoint even if it was exported in the shell:
OTEL_EXPORTER_OTLP_ENDPOINT= docker compose up -d --force-recreate --wait app
docker compose exec -T app python -c "import os; assert not os.environ.get('OTEL_EXPORTER_OTLP_ENDPOINT'); print('telemetry endpoint empty')"
OTEL_EXPORTER_OTLP_ENDPOINT= make integration
OTEL_EXPORTER_OTLP_ENDPOINT= make e2e
```

The fixture and payload never enter recorded evidence. See
[VALIDATION.md](VALIDATION.md) for the Engineer's timestamped results.
