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
	. ${VENV}/bin/activate && ${VENV}/bin/black src tests
	. ${VENV}/bin/activate && ${VENV}/bin/ruff check --fix src tests

test:
	. ${VENV}/bin/activate && ${VENV}/bin/pytest -q
