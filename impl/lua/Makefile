MAKEFILE_DIR := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
REPO_ROOT := $(abspath $(MAKEFILE_DIR)/../..)
SRC_DIR := $(MAKEFILE_DIR)src/main/lua
TEST_DIR := $(MAKEFILE_DIR)src/test/lua
BIN_DIR := $(MAKEFILE_DIR)bin
LUA ?= lua
LUAC ?= luac
LUA_SOURCES := $(shell find "$(MAKEFILE_DIR)src" -name '*.lua' -print | sort)

.PHONY: all build generate check-generated syntax test lint check clean

all: build

generate:
	cd "$(REPO_ROOT)" && python3 -B generate_json_code.py --target lua

check-generated:
	cd "$(REPO_ROOT)" && python3 -B generate_json_code.py --target lua --check

syntax: generate
	$(LUAC) -p $(LUA_SOURCES)

build: syntax
	rm -rf "$(BIN_DIR)/app"
	mkdir -p "$(BIN_DIR)/app"
	cp -R "$(SRC_DIR)/." "$(BIN_DIR)/app/"
	cp "$(MAKEFILE_DIR)src/launcher/liff" "$(BIN_DIR)/liff"
	chmod 755 "$(BIN_DIR)/liff"

test: check-generated syntax
	$(LUA) "$(TEST_DIR)/core_test.lua" "$(REPO_ROOT)"
	$(LUA) "$(TEST_DIR)/cli_test.lua" "$(REPO_ROOT)"

lint: check-generated syntax
	cd "$(REPO_ROOT)" && python3 -B -c 'from pathlib import Path; paths=list(Path("impl/lua/src").rglob("*.lua")); bad=[f"{p}:{n}" for p in paths for n,line in enumerate(p.read_text(encoding="utf-8").splitlines(),1) if line.rstrip()!=line or "\t" in line]; assert not bad, "Lua whitespace errors: " + ", ".join(bad)'

check: test lint

clean:
	rm -rf "$(BIN_DIR)"
