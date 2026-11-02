# Production operations

## v0 deployment shape

The v0 is intentionally small: one Linux host runs Caddy, the FastAPI image,
and Neo4j Community through `compose.production.yml`. Caddy owns ports 80/443
and provisions HTTPS. Neo4j has no host port and is reachable only from the
private Compose network. The public proxy returns 404 for the editorial page,
its JavaScript, and all editorial API routes. Content review remains a local or
private post-v0 workflow.

This topology is appropriate for an initial low-traffic release. Move Neo4j to
managed infrastructure or a separate private host before introducing multiple
application replicas or availability requirements.

## First deployment

Provision a Linux host with Docker Engine, the Compose plugin, a persistent
disk, and inbound TCP 80/443 plus UDP 443. Point the chosen domain's A/AAAA
records to that host. Do not open 7474 or 7687.

On the host:

```bash
cp .env.production.example .env.production
# Replace DOMAIN and both secrets before continuing.
docker compose --env-file .env.production -f compose.production.yml config --quiet
docker compose --env-file .env.production -f compose.production.yml build api
docker compose --env-file .env.production -f compose.production.yml up -d neo4j
docker compose --env-file .env.production -f compose.production.yml run --rm api elden-lore-migrate
docker compose --env-file .env.production -f compose.production.yml run --rm api elden-lore-audit
docker compose --env-file .env.production -f compose.production.yml run --rm api elden-lore-import
docker compose --env-file .env.production -f compose.production.yml up -d
```

On the current macOS external volume, AppleDouble metadata can confuse Docker's
context walker. `make prod-build` uses a temporary clean context and leaves the
workspace untouched. Linux hosts and clean Git checkouts can build directly.

Verify `https://YOUR_DOMAIN/health`, `/ready`, the home page, an entity page,
and an unsupported question. Confirm that `/editorial.html` and
`/api/v1/editorial/dashboard` both return 404 through the public hostname.

## Render Free with AuraDB Free

For the no-cost v0, `render.yaml` defines a Docker web service in Frankfurt.
Set the three prompted secrets to the AuraDB connection URI, username, and
password. Keep `NEO4J_DATABASE=neo4j`, `EDITORIAL_ENABLED=false`, and
`ANSWER_GENERATOR=deterministic`. The application listens on port 10000 and
Render checks `/ready`.

Render Free has no one-off jobs or shell access. Before the first deploy, load
the remote graph from a trusted workstation by setting the AuraDB variables in
the shell and running the migration, audit, and import commands locally. Do not
write Aura credentials to `.env`, commit them, or paste them into issue trackers.

```bash
NEO4J_URI='neo4j+s://YOUR_INSTANCE.databases.neo4j.io' \
NEO4J_USERNAME='neo4j' \
NEO4J_PASSWORD='YOUR_LOCAL_SECRET' \
NEO4J_DATABASE='neo4j' make migrate

NEO4J_URI='neo4j+s://YOUR_INSTANCE.databases.neo4j.io' \
NEO4J_USERNAME='neo4j' \
NEO4J_PASSWORD='YOUR_LOCAL_SECRET' \
NEO4J_DATABASE='neo4j' make audit

NEO4J_URI='neo4j+s://YOUR_INSTANCE.databases.neo4j.io' \
NEO4J_USERNAME='neo4j' \
NEO4J_PASSWORD='YOUR_LOCAL_SECRET' \
NEO4J_DATABASE='neo4j' make import
```

Create the Render service only after the graph import succeeds. The free
service receives an `onrender.com` hostname and sleeps after inactivity; AuraDB
Free may also pause after extended inactivity.

## Release and rollback

Before every release, run `make check`, `make audit`, and `make evaluate` in a
connected test environment. Tag the image with an immutable release identifier
through `IMAGE_TAG`; do not use `latest` for a release you may need to roll
back. Take a data-volume snapshot before migrations or imports.

To roll back application code, restore the previous `IMAGE_TAG` and recreate
`api` and `proxy`. If a release changed graph data, stop writes and restore the
pre-release volume snapshot before starting the previous application image.
Never attempt a data rollback by rerunning older migrations.

## Backup and recovery

Neo4j Community does not provide the online backup workflow of Enterprise.
For v0, use crash-consistent snapshots of the persistent Docker volume/disk.
Schedule them daily, retain at least seven daily and four weekly snapshots, and
encrypt them at rest. Before a planned migration, stop the API, stop Neo4j,
take an offline snapshot, then restart and verify `/ready`.

A backup is not considered valid until restored to a separate host and checked
with `/ready`, a representative graph query, and the deterministic evaluation
suite. Perform this recovery rehearsal before launch and after material schema
changes.

## Required services

- a Neo4j 5.26+ database with persistent backups;
- a container or Python host for the FastAPI application;
- HTTPS and a domain, normally through a managed reverse proxy;
- optional OpenAI API billing and a project-scoped API key for generative prose.

ChatGPT subscriptions do not include API usage. The deterministic answer path
works without an OpenAI account and remains the recommended initial launch mode.

## Secrets and database roles

Set `APP_ENV=production`, a random `EDITORIAL_TOKEN`, and production Neo4j
credentials through the host's secret manager. Never commit `.env`. The v0
runtime retains database write access for reader feedback, but Caddy blocks the
editorial surface. Keep host access restricted and rotate both secrets after
any suspected disclosure.

## Edge controls

Terminate TLS at the proxy. The application caps request bodies and applies
per-process limits to `/api/v1/answers` and `/api/v1/feedback`; replace or
supplement these with shared edge rate limiting when running multiple workers.
Keep the API security headers enabled. Do not expose Neo4j Browser or Bolt to
the public internet.

Back up Neo4j before migrations, run `make check`, `make migrate`, `make audit`,
and `make import`, then verify `/ready`. Retain feedback only as long as needed;
comments must not collect email addresses or other unnecessary personal data.

## Feedback integrity

Feedback is moderation input, not canonical evidence. It is stored against a
deterministic answer snapshot and referenced claims. New submissions are
pending; only approved entries enter the aggregate community signal, and at
least three approved ratings are required before a directional signal appears.
Editors must investigate negative signals against primary evidence before
changing a claim's review state or confidence.
