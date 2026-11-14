# Local observability

From the repository root, with Docker Compose v2 installed:

```sh
make obs-up
docker compose -f observability/docker-compose.yaml ps
```

This is the separate `gradematch-observability` project. App `make up/down`
commands and Render are independent. All published ports bind to localhost:
Grafana 3000, Prometheus 9090, Loki 3100, Tempo 3200, Collector OTLP HTTP/protobuf
4318 and Collector health 13133. Collector Prometheus 8889 and Tempo OTLP
4317/4318 are internal only. This unauthenticated development stack is for local
use; Grafana's initial login is `admin` / `admin` and prompts for a new password.
Open http://localhost:3000 and Connections → Data sources: Prometheus, Loki and
Tempo are provisioned automatically. Select each and use Save & test.

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
Application connection and smoke instructions are added separately for #131.

For an executable readiness/provisioning assertion, run
`python3 observability/check.py` (set `GRAFANA_PASSWORD` if changed).
