# Future roadmap and scaling

This roadmap outlines a pragmatic crawl → walk → run path for deploying and scaling the bot.

## Phase 1 — Raspberry Pi (crawl)

Goal: Single-strategy, paper trading; prove stability and safety.

- Hardware
  - Raspberry Pi 4/5 (4GB+), reliable power, microSD (prefer SSD via USB 3.0)
  - Network with access to a host running IBKR Gateway/TWS (can be same LAN)
- OS & prerequisites
  - 64-bit Linux (Raspberry Pi OS or Ubuntu Server)
  - Python 3.11+, system packages for scientific Python:
    - Debian/Ubuntu: `build-essential libatlas-base-dev libopenblas-dev gfortran python3-dev`
- Setup
  - Clone repo; create venv; install `requirements.txt`
  - Configure `configs/settings.yaml` (use `dry_run: true` initially)
  - Point `broker.host`/`broker.port` at your IBKR Gateway (paper mode)
  - Set minimal symbols (e.g., SPY), longer `schedule.interval_seconds` (e.g., 300)
- Run & manage
  - `./scripts/run_bot.sh` for foreground
  - Optional: install as a user systemd service with `./scripts/install_systemd.sh`
- Constraints & tips
  - Limited CPU/RAM: avoid too many symbols; prefer simple indicators
  - Use JSON logs in `logs/` for quick diagnostics

## Phase 2 — R620 or similar server (walk)

Goal: Multi-strategy, multiple symbols, CI/CD, containerized deployment.

- Hardware
  - 2× Xeon-class CPU, 64GB RAM+, SSD/NVMe storage, stable connectivity
- CI/CD & quality gates
  - GitHub Actions: black --check, ruff, mypy, pytest (already configured)
  - Pre-commit hooks (black, ruff, mypy) to enforce consistent style locally
- Containerization
  - Build with `Dockerfile`; run with `docker-compose.yml`
  - Optional overlay: `docker-compose.gateway.yml` to run IBKR Gateway side-by-side (paper)
  - Mount `configs/` read-only and `logs/` for persistence
- Concurrency & monitoring
  - Increase `schedule.max_concurrent_symbols` based on CPU/network
  - Set `monitoring.heartbeat_url`, Slack/Telegram webhooks for alerts
- Operations
  - Use `.env` for secrets; keep it out of VCS (gitignored) and tighten permissions
  - Rotate logs (handled via loguru) and centralize if desired

## Phase 3 — GPU-capable server (run)

Goal: Extend with deep-learning strategies and larger-scale data workflows.

- Hardware
  - NVIDIA GPU (e.g., RTX A4000/6000), sufficient VRAM (16GB+)
  - Fast storage (NVMe), high-memory system (128GB+) for data pipelines
- Platform & dependencies
  - CUDA/cuDNN when introducing DL libs (PyTorch/TensorFlow)
  - Consider isolating ML pipelines into separate services/containers
- Architecture evolution
  - Event-driven components (e.g., Redis/Kafka) to decouple data ingest, signal generation, and execution
  - Model serving as a microservice; feature stores and data retention policies
  - Orchestration (Kubernetes or Nomad) for scheduling, health checks, and scaling
- Observability & safety
  - Metrics (Prometheus/Grafana), tracing/log aggregation
  - Guardrails: circuit breakers on risk checks, stricter position limits
  - Secrets management (Vault, AWS/GCP secret stores)

## Security & governance (all phases)

- Keep `.env` out of VCS; restrict file permissions (chmod 600 on Unix)
- Use `dry_run: true` when validating new environments
- Never log secrets; review logs before sharing
- Backups for configs/logs; monitor disk space

## Configuration checklist

- `configs/settings.yaml`
  - `broker.host/port/client_id/read_only`
  - `symbols`, `mode`, `dry_run`
  - `schedule.interval_seconds`, `schedule.max_concurrent_symbols`
  - `risk` (max_daily_loss_pct, max_risk_pct_per_trade, take_profit_pct, stop_loss_pct)
  - `options` (moneyness, min_volume, max_spread_pct)
  - `monitoring` (heartbeat_url, slack/telegram)
- `.env`
  - IBKR credentials if needed by your gateway container or launcher

## Next steps

- Add a FakeBroker-backed integration test for concurrency and journaling
- Optional: add docker healthchecks and a minimal status endpoint for liveness probes
- Consider daily P&L summary generation and artifact archiving (reports)
