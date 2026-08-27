MAKEFILE_DIR := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
REPO_ROOT := $(abspath $(MAKEFILE_DIR)/../..)
BIN_DIR := $(MAKEFILE_DIR)bin
OUTPUT_BINARY := $(BIN_DIR)/liff

.PHONY: all build generate check-generated test lint check clean

all: build

generate:
	cd "$(REPO_ROOT)" && python3 -B generate_json_code.py --target go

check-generated:
	cd "$(REPO_ROOT)" && python3 -B generate_json_code.py --target go --check

build: generate
	mkdir -p "$(BIN_DIR)"
	cd "$(MAKEFILE_DIR)" && go build -trimpath -o "$(OUTPUT_BINARY)" ./cmd/liff

test: check-generated
	cd "$(MAKEFILE_DIR)" && go test ./...

lint:
	cd "$(MAKEFILE_DIR)" && test -z "$$(gofmt -l .)"
	cd "$(MAKEFILE_DIR)" && go vet ./...

check: test lint

clean:
	cd "$(MAKEFILE_DIR)" && go clean ./...
	rm -rf "$(BIN_DIR)"
