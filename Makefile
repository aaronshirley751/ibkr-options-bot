VENV=.venv
PYTHON=${PYTHON:-python3}
PIP=${PIP:-${PYTHON} -m pip}

.PHONY: venv fmt test

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
