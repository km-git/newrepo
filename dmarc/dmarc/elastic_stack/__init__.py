"""Optional dockerized parsedmarc + Elasticsearch + Kibana stack."""

from pathlib import Path

COMPOSE_ELASTIC = Path(__file__).resolve().parents[2] / "docker-compose.yml"
