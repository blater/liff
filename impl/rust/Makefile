MAKEFILE_DIR := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
REPO_ROOT := $(abspath $(MAKEFILE_DIR)/../..)
MANIFEST := $(MAKEFILE_DIR)Cargo.toml
TARGET_DIR := $(MAKEFILE_DIR)target
BIN_DIR := $(MAKEFILE_DIR)bin
RELEASE_BINARY := $(TARGET_DIR)/release/liff
OUTPUT_BINARY := $(BIN_DIR)/liff

.PHONY: all build generate check-generated test lint check clean

all: build

generate:
	cd "$(REPO_ROOT)" && python3 -B generate_json_code.py --target rust

check-generated:
	cd "$(REPO_ROOT)" && python3 -B generate_json_code.py --target rust --check

build: generate
	cargo build --manifest-path "$(MANIFEST)" --release --locked
	mkdir -p "$(BIN_DIR)"
	cp "$(RELEASE_BINARY)" "$(OUTPUT_BINARY)"

test: check-generated
	cargo test --manifest-path "$(MANIFEST)" --locked

lint:
	cargo fmt --manifest-path "$(MANIFEST)" --all --check
	cargo clippy --manifest-path "$(MANIFEST)" --all-targets --locked -- -D warnings

check: test lint

clean:
	cargo clean --manifest-path "$(MANIFEST)"
	rm -rf "$(BIN_DIR)"
