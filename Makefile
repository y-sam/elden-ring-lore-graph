UV_ENVIRONMENT ?= /tmp/elden-lore-venv
UV_CACHE ?= /tmp/elden-lore-uv-cache
UV_RUN = UV_PROJECT_ENVIRONMENT=$(UV_ENVIRONMENT) UV_CACHE_DIR=$(UV_CACHE) uv run

.PHONY: sync lint test check run migrate import import-aura audit corpus-validate corpus-report evaluate prod-config prod-build

sync:
	UV_PROJECT_ENVIRONMENT=$(UV_ENVIRONMENT) UV_CACHE_DIR=$(UV_CACHE) uv sync --extra dev --link-mode=copy

lint:
	$(UV_RUN) ruff check .

test:
	$(UV_RUN) pytest

check: lint test

run:
	$(UV_RUN) elden-lore-api

migrate:
	$(UV_RUN) elden-lore-migrate

import:
	$(UV_RUN) elden-lore-import

import-aura:
	bash scripts/import-aura.sh

audit:
	$(UV_RUN) elden-lore-audit

corpus-validate:
	$(UV_RUN) elden-lore-audit

corpus-report:
	$(UV_RUN) elden-lore-audit

evaluate:
	$(UV_RUN) elden-lore-evaluate

prod-config:
	docker compose --env-file .env.production -f compose.production.yml config --quiet

prod-build:
	sh scripts/build-production-image.sh elden-ring-lore-graph:$${IMAGE_TAG:-local}
