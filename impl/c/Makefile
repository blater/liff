MAKEFILE_DIR := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
REPO_ROOT := $(abspath $(MAKEFILE_DIR)/../..)
BUILD_DIR := $(MAKEFILE_DIR)build
OBJECT_DIR := $(BUILD_DIR)/objects
BIN_DIR := $(MAKEFILE_DIR)bin
INCLUDES := -I"$(MAKEFILE_DIR)include" -I"$(MAKEFILE_DIR)src"
WARNINGS := -Wall -Wextra -Wpedantic -Werror
STANDARD := -std=c17
CC ?= cc
AR ?= ar
CFLAGS ?= -O2

CORE_SOURCES := \
	$(MAKEFILE_DIR)src/liff.c \
	$(MAKEFILE_DIR)src/normalize.c \
	$(MAKEFILE_DIR)src/dictionary_generated.c
CORE_OBJECTS := \
	$(OBJECT_DIR)/liff.o \
	$(OBJECT_DIR)/normalize.o \
	$(OBJECT_DIR)/dictionary_generated.o

$(CORE_OBJECTS): generate

.PHONY: all build generate check-generated core test lint check clean

all: build

generate:
	cd "$(REPO_ROOT)" && python3 -B generate_json_code.py --target c

check-generated:
	cd "$(REPO_ROOT)" && python3 -B generate_json_code.py --target c --check

$(OBJECT_DIR)/%.o: $(MAKEFILE_DIR)src/%.c
	mkdir -p "$(OBJECT_DIR)"
	$(CC) $(STANDARD) $(CFLAGS) $(WARNINGS) $(INCLUDES) -c "$<" -o "$@"

core: generate $(CORE_OBJECTS)
	$(AR) rcs "$(BUILD_DIR)/libliff.a" $(CORE_OBJECTS)

build: core
	mkdir -p "$(BIN_DIR)"
	$(CC) $(STANDARD) $(CFLAGS) $(WARNINGS) $(INCLUDES) \
		"$(MAKEFILE_DIR)src/main.c" "$(MAKEFILE_DIR)src/cli.c" \
		"$(BUILD_DIR)/libliff.a" -o "$(BIN_DIR)/liff"

test: check-generated core
	$(CC) $(STANDARD) -O0 -g $(WARNINGS) $(INCLUDES) \
		"$(MAKEFILE_DIR)src/main.c" "$(MAKEFILE_DIR)src/cli.c" \
		"$(BUILD_DIR)/libliff.a" -o "$(BUILD_DIR)/liff-test"
	$(CC) $(STANDARD) -O0 -g $(WARNINGS) $(INCLUDES) \
		"$(MAKEFILE_DIR)tests/test_driver.c" "$(BUILD_DIR)/libliff.a" \
		-o "$(BUILD_DIR)/test-driver"
	python3 -B "$(MAKEFILE_DIR)tests/test_conformance.py" \
		--driver "$(BUILD_DIR)/test-driver" \
		--cli "$(BUILD_DIR)/liff-test" \
		--root "$(REPO_ROOT)"

lint: check-generated
	$(CC) $(STANDARD) $(WARNINGS) $(INCLUDES) -fsyntax-only \
		$(CORE_SOURCES) "$(MAKEFILE_DIR)src/cli.c" "$(MAKEFILE_DIR)src/main.c" \
		"$(MAKEFILE_DIR)tests/test_driver.c"
	cd "$(REPO_ROOT)" && python3 -B -c 'from pathlib import Path; paths=list(Path("impl/c").rglob("*.c"))+list(Path("impl/c").rglob("*.h")); bad=[f"{p}:{n}" for p in paths for n,line in enumerate(p.read_text(encoding="utf-8").splitlines(),1) if line.rstrip()!=line or "\t" in line]; assert not bad, "C whitespace errors: " + ", ".join(bad)'

check: test lint

clean:
	rm -rf "$(BUILD_DIR)" "$(BIN_DIR)"
