VENV=.venv
PYTHON=${PYTHON:-python3}
PIP=${PIP:-${PYTHON} -m pip}

.PHONY: venv fmt test ibkr-deps ibkr-test

venv:
	${PYTHON} -m venv ${VENV}
	. ${VENV}/bin/activate && ${PIP} install --upgrade pip
	. ${VENV}/bin/activate && ${PIP} install -r requirements.txt
	. ${VENV}/bin/activate && ${PIP} install -r requirements-dev.txt

fmt:
	@if [ -x "${VENV}/bin/black" ]; then \
		${VENV}/bin/black src tests; \
		${VENV}/bin/ruff check --fix src tests; \
	else \
		black src tests; \
		ruff check --fix src tests; \
	fi

test:
	@if [ -x "${VENV}/bin/pytest" ]; then \
		${VENV}/bin/pytest -q; \
	else \
		pytest -q; \
	fi

ibkr-deps:
	@if [ -x "${VENV}/bin/pip" ]; then \
		${VENV}/bin/pip install -r requirements-ibkr.txt; \
	else \
		${PIP} install -r requirements-ibkr.txt; \
	fi

ibkr-test: ibkr-deps
	@if [ -x "${VENV}/bin/python" ]; then \
		${VENV}/bin/python test_ibkr_connection.py --host $${IBKR_HOST:-127.0.0.1} --port $${IBKR_PORT:-4002} --client-id $${IBKR_CLIENT_ID:-101} --symbol $${TEST_SYMBOL:-SPY}; \
	else \
		${PYTHON} test_ibkr_connection.py --host $${IBKR_HOST:-127.0.0.1} --port $${IBKR_PORT:-4002} --client-id $${IBKR_CLIENT_ID:-101} --symbol $${TEST_SYMBOL:-SPY}; \
	fi
