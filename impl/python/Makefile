MAKEFILE_DIR := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
REPO_ROOT := $(abspath $(MAKEFILE_DIR)/../..)
SRC_DIR := $(MAKEFILE_DIR)src
BIN_DIR := $(MAKEFILE_DIR)bin
OUTPUT_APP := $(BIN_DIR)/liff

.PHONY: all build generate check-generated test lint check clean

all: build

generate:
	cd "$(REPO_ROOT)" && python3 -B generate_json_code.py --target python_impl

check-generated:
	cd "$(REPO_ROOT)" && python3 -B generate_json_code.py --target python_impl --check

build: generate
	mkdir -p "$(BIN_DIR)"
	python3 -m zipapp "$(SRC_DIR)" --main liff.cli:main --python '/usr/bin/env python3' --compress --output "$(OUTPUT_APP)"

test: check-generated
	cd "$(MAKEFILE_DIR)" && PYTHONPATH="$(SRC_DIR)" python3 -B -m unittest discover -s tests -p 'test_*.py'

lint:
	cd "$(MAKEFILE_DIR)" && python3 -B -c 'import ast, pathlib; paths = sorted(pathlib.Path("src").rglob("*.py")) + sorted(pathlib.Path("tests").rglob("*.py")); [ast.parse(path.read_text(encoding="utf-8"), filename=str(path)) for path in paths]'

check: test lint

clean:
	rm -rf "$(BIN_DIR)"
	find "$(MAKEFILE_DIR)" -type d -name __pycache__ -prune -exec rm -rf {} +
