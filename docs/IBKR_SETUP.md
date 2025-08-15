IBKR Setup on Raspberry Pi (Gateway or Client Portal API)
=========================================================

This guide helps you install and run either IB Gateway (recommended for this bot) or the Client Portal API locally, configure API access, and verify connectivity from the bot.

Prerequisites
-------------
- Raspberry Pi 4/5 running 64‑bit Linux (Raspberry Pi OS or Ubuntu Server)
- Python 3.11+
- Docker and Docker Compose (for the provided compose files)

Option A: IB Gateway (paper trading)
------------------------------------

1) Prepare environment variables

- Copy `.env.example` to `.env` and set at minimum:
	- `IBKR_USERNAME=your_paper_username`
	- `IBKR_PASSWORD=your_paper_password`
	- Optional: `TZ=America/New_York`

2) Start Gateway with the compose overlay

- Use the overlay provided in this repo to run Gateway side‑by‑side with the bot if desired:

```bash
# Gateway only
docker compose -f docker-compose.gateway.yml up --build

# Bot + Gateway together (overlay). Ensure .env contains user/pass.
docker compose -f docker-compose.yml -f docker-compose.gateway.yml up --build
```

The Gateway exposes the IB API on port 4002 (paper). The bot defaults to `IBKR_HOST=127.0.0.1`, `IBKR_PORT=4002`.

3) Verify API settings in Gateway

- In the Gateway/TWS API settings: enable API access, set Socket Port to 4002 (paper), and allow connections from the bot’s IP. For headless containers, the compose image sets sensible defaults.

Option B: Client Portal API
---------------------------

If you prefer the Client Portal Web API (HTTP/WebSocket), run the official container/service on the Pi and expose its port. This project primarily uses the TWS/Gateway socket API via `ib_insync`, but you can run Client Portal alongside for other tooling.

Environment & configuration
---------------------------

- Ensure the following env vars are set for the bot:
	- `IBKR_HOST` (default `127.0.0.1`)
	- `IBKR_PORT` (default `4002` for paper)
	- `IBKR_CLIENT_ID` (default `101` in `configs/settings.yaml`)
- Edit `configs/settings.yaml` and align `broker.host/port/client_id` with your environment. Set `dry_run: true` while testing.

Connectivity tests
------------------

Use the provided connection test script to validate the setup. It will:
- Connect to Gateway
- Fetch a stock snapshot (e.g., SPY)
- Fetch a forex snapshot (EURUSD)
- Fetch a small option chain and snapshot an ATM option
- Optionally attempt Level 2 depth if supported
- Request short historical bars

Run the tests (requires `ib_insync`):

```bash
python test_ibkr_connection.py --host ${IBKR_HOST:-127.0.0.1} --port ${IBKR_PORT:-4002} --client-id ${IBKR_CLIENT_ID:-101}
```

Troubleshooting
---------------

- Authentication failures: confirm `.env` credentials and that the account is in paper mode when using port 4002.
- No market data: Ensure your IBKR account has market data subscriptions; many symbols require entitlements for real‑time quotes or depth.
- Connection refused: Confirm Gateway container is running and listening on 4002; check network/firewall rules.
- Timeouts: The test script uses short timeouts and will log warnings; increase `--timeout` if your network is slow.

Next steps
----------

- Once connectivity is verified, set `dry_run: false` only when you are confident in your configuration and have appropriate risk limits in `configs/settings.yaml`.
- Review `README.md` and `ROADMAP.md` for deployment guidance and operational best practices.

How to use (SSH into the Raspberry Pi)
--------------------------------------

1) SSH into your Pi from your dev machine:

```bash
ssh pi@<pi-host-or-ip>
```

2) Ensure Docker and Compose plugin are installed on the Pi. Then clone or sync this repo:

```bash
git clone https://github.com/aaronshirley751/ibkr-options-bot.git
cd ibkr-options-bot
```

3) Create `.env` with your paper credentials and timezone:

```bash
cp .env.example .env
vim .env  # set IBKR_USERNAME, IBKR_PASSWORD, TZ
```

4) Launch IB Gateway via Docker Compose overlay (paper mode):

```bash
docker compose -f docker-compose.gateway.yml up --build -d
```

5) From the same Pi session (or via a venv), run the connectivity test:

```bash
make venv
make ibkr-test
# Optional: test what-if bracket order
TEST_SYMBOL=SPY ${MAKE} ibkr-test IBKR_HOST=127.0.0.1 IBKR_PORT=4002 IBKR_CLIENT_ID=101 -- --place-test-order
```

6) Review JSON-like output lines to confirm quotes, bars, and depth (if subscribed). Stop Gateway when done:

```bash
docker compose -f docker-compose.gateway.yml down
```
