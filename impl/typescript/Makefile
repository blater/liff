MAKEFILE_DIR := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
REPO_ROOT := $(abspath $(MAKEFILE_DIR)/../..)
BUILD_DIR := $(MAKEFILE_DIR)build
BIN_DIR := $(MAKEFILE_DIR)bin
TSC ?= tsc
NODE ?= node

.PHONY: all build generate check-generated compile-main compile-test test lint check clean

all: build

generate:
	cd "$(REPO_ROOT)" && python3 -B generate_json_code.py --target typescript

check-generated:
	cd "$(REPO_ROOT)" && python3 -B generate_json_code.py --target typescript --check

compile-main: generate
	rm -rf "$(BUILD_DIR)/app"
	cd "$(MAKEFILE_DIR)" && $(TSC) --project tsconfig.json --pretty false

compile-test: compile-main
	rm -rf "$(BUILD_DIR)/test"
	cd "$(MAKEFILE_DIR)" && $(TSC) --project tsconfig.test.json --pretty false

build: compile-main
	rm -rf "$(BIN_DIR)/app"
	mkdir -p "$(BIN_DIR)/app"
	cp "$(BUILD_DIR)/app/"*.js "$(BIN_DIR)/app/"
	cp "$(MAKEFILE_DIR)src/launcher/liff" "$(BIN_DIR)/liff"
	chmod 755 "$(BIN_DIR)/liff"

test: check-generated compile-test
	$(NODE) "$(BUILD_DIR)/test/test/ts/core.test.js" "$(REPO_ROOT)"
	$(NODE) "$(BUILD_DIR)/test/test/ts/cli.test.js"

lint: check-generated
	cd "$(MAKEFILE_DIR)" && $(TSC) --project tsconfig.json --noEmit --pretty false
	cd "$(REPO_ROOT)" && python3 -B -c 'from pathlib import Path; paths=list(Path("impl/typescript/src").rglob("*.ts")); bad=[f"{p}:{n}" for p in paths for n,line in enumerate(p.read_text(encoding="utf-8").splitlines(),1) if line.rstrip()!=line or "\t" in line]; assert not bad, "TypeScript whitespace errors: " + ", ".join(bad)'

check: test lint

clean:
	rm -rf "$(BUILD_DIR)" "$(BIN_DIR)"
