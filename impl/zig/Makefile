MAKEFILE_DIR := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
REPO_ROOT := $(abspath $(MAKEFILE_DIR)/../..)
BIN_DIR := $(MAKEFILE_DIR)bin
OUTPUT_BINARY := $(BIN_DIR)/liff
CACHE_FLAGS := --cache-dir "$(MAKEFILE_DIR).zig-cache" --global-cache-dir "$(MAKEFILE_DIR).zig-global-cache"
ZIG ?= zig

.PHONY: all build generate check-generated test lint check clean

all: build

generate:
	cd "$(REPO_ROOT)" && python3 -B generate_json_code.py --target zig

check-generated:
	cd "$(REPO_ROOT)" && python3 -B generate_json_code.py --target zig --check

build: generate
	mkdir -p "$(BIN_DIR)"
	cd "$(REPO_ROOT)" && $(ZIG) build-exe impl/zig/src/main.zig -O ReleaseSafe -femit-bin="$(OUTPUT_BINARY)" $(CACHE_FLAGS)

test: check-generated
	cd "$(REPO_ROOT)" && $(ZIG) test impl/zig/src/tests.zig $(CACHE_FLAGS)
	cd "$(REPO_ROOT)" && $(ZIG) test impl/zig/src/main.zig $(CACHE_FLAGS)

lint:
	cd "$(REPO_ROOT)" && $(ZIG) fmt --check impl/zig/src

check: test lint

clean:
	rm -rf "$(BIN_DIR)" "$(MAKEFILE_DIR).zig-cache" "$(MAKEFILE_DIR).zig-global-cache"
