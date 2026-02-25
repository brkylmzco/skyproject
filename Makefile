.PHONY: init run test lint clean docker-build docker-run

init:
	skyproject init

run:
	skyproject run

run-cycles:
	skyproject run --cycles $(or $(CYCLES),5)

status:
	skyproject status

test:
	pytest -v

lint:
	ruff check skyproject/

format:
	ruff format skyproject/

install:
	pip install -e ".[dev]"

clean:
	rm -rf data/tasks/* data/logs/* data/vector_db/*
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

docker-build:
	docker compose build

docker-run:
	docker compose up

docker-down:
	docker compose down
