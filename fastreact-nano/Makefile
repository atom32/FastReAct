# FastReAct Nano - Makefile
# Convenient commands for development and deployment

.PHONY: help install test lint format build release clean docker docker-build docker-up docker-down

# Default target
.DEFAULT_GOAL := help

# Colors
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[1;33m
NC := \033[0m

## help: Show this help message
help:
	@echo '$(BLUE)FastReAct Nano - Available Commands$(NC)'
	@echo ''
	@sed -n 's/^##//p' ${MAKEFILE_LIST} | column -t -s ':' | sed -e 's/^/ /'
	@echo ''

## install: Install package with all features
install:
	@echo '$(GREEN)Installing fastreact-nano[all]...$(NC)'
	pip install -e ".[all]"

## install-dev: Install in development mode
install-dev:
	@echo '$(GREEN)Installing in development mode...$(NC)'
	pip install -e ".[all,dev]"

## test: Run all tests
test:
	@echo '$(GREEN)Running tests...$(NC)'
	python3 -m pytest tests/ -v --tb=short

## test-unit: Run unit tests only
test-unit:
	@echo '$(GREEN)Running unit tests...$(NC)'
	python3 -m pytest tests/unit/ -v

## test-integration: Run integration tests
test-integration:
	@echo '$(GREEN)Running integration tests...$(NC)'
	python3 -m pytest tests/integration/ -v

## test-coverage: Run tests with coverage report
test-coverage:
	@echo '$(GREEN)Running tests with coverage...$(NC)'
	python3 -m pytest tests/ --cov=src/fastreact --cov-report=html

## lint: Run linters
lint:
	@echo '$(GREEN)Running linters...$(NC)'
	ruff check src/ tests/
	mypy src/

## format: Format code with black and ruff
format:
	@echo '$(GREEN)Formatting code...$(NC)'
	black src/ tests/
	ruff check src/ tests/ --fix

## check: Run all quality checks (lint + format check)
check: lint format
	@echo '$(GREEN)All quality checks passed!$(NC)'

## build: Build Python packages (sdist + wheel)
build:
	@echo '$(GREEN)Building packages...$(NC)'
	python3 -m build
	@echo '$(GREEN)Build complete: dist/$(NC)'

## release-patch: Bump patch version and create release
release-patch:
	@echo '$(YELLOW)Creating patch release...$(NC)'
	./release.sh patch

## release-minor: Bump minor version and create release
release-minor:
	@echo '$(YELLOW)Creating minor release...$(NC)'
	./release.sh minor

## release-major: Bump major version and create release
release-major:
	@echo '$(YELLOW)Creating major release...$(NC)'
	./release.sh major

## clean: Clean build artifacts
clean:
	@echo '$(GREEN)Cleaning build artifacts...$(NC)'
	rm -rf dist/ build/ *.egg-info release/
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	@echo '$(GREEN)Clean complete!$(NC)'

## docker-build: Build Docker images
docker-build:
	@echo '$(GREEN)Building Docker images...$(NC)'
	docker-compose build

## docker-up: Start all services
docker-up:
	@echo '$(GREEN)Starting Docker services...$(NC)'
	docker-compose up -d
	@echo '$(GREEN)Services started!$(NC)'
	@echo 'HTTP daemon: http://localhost:18741'

## docker-down: Stop all services
docker-down:
	@echo '$(GREEN)Stopping Docker services...$(NC)'
	docker-compose down

## docker-logs: View service logs
docker-logs:
	docker-compose logs -f

## docker-ps: Show running containers
docker-ps:
	docker-compose ps

## docker-dev: Start development environment
docker-dev:
	@echo '$(GREEN)Starting dev environment...$(NC)'
	docker-compose --profile dev up

## docker-monitoring: Start with monitoring (Prometheus + Grafana)
docker-monitoring:
	@echo '$(GREEN)Starting with monitoring...$(NC)'
	docker-compose --profile monitoring up -d
	@echo 'Prometheus: http://localhost:9090'
	@echo 'Grafana: http://localhost:3000'

## docker-clean: Remove Docker containers and volumes
docker-clean:
	@echo '$(YELLOW)Removing Docker containers and volumes...$(NC)'
	docker-compose down -v
	docker system prune -f

## e2e-test: Run end-to-end tests
e2e-test:
	@echo '$(GREEN)Running E2E tests...$(NC)'
	python3 test_e2e_multitenant_graphrag.py

## verify: Run full verification (tests + lint + build)
verify: test lint build
	@echo '$(GREEN)$(BLUE)✅ All verification checks passed!$(NC)'

## all: Run install, test, lint
all: install test lint
	@echo '$(GREEN)$(BLUE)✅ Ready for development!$(NC)'
