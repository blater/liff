MAKEFILE_DIR := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
REPO_ROOT := $(abspath $(MAKEFILE_DIR)/../..)
BUILD_DIR := $(MAKEFILE_DIR)build
MAIN_CLASSES := $(BUILD_DIR)/classes
TEST_CLASSES := $(BUILD_DIR)/test-classes
BIN_DIR := $(MAKEFILE_DIR)bin
MAIN_SOURCES := $(shell find "$(MAKEFILE_DIR)src/main/java" -name '*.java' -print | sort)
TEST_SOURCES := $(shell find "$(MAKEFILE_DIR)src/test/java" -name '*.java' -print | sort)
JAVAC ?= javac
JAVA ?= java
JAR ?= jar
JAVA_FLAGS := --release 17 -encoding UTF-8 -Xlint:all -Werror

.PHONY: all build generate check-generated compile-main compile-test test lint check clean

all: build

generate:
	cd "$(REPO_ROOT)" && python3 -B generate_json_code.py --target java

check-generated:
	cd "$(REPO_ROOT)" && python3 -B generate_json_code.py --target java --check

compile-main: generate
	rm -rf "$(MAIN_CLASSES)"
	mkdir -p "$(MAIN_CLASSES)"
	$(JAVAC) $(JAVA_FLAGS) -d "$(MAIN_CLASSES)" $(MAIN_SOURCES)

compile-test: compile-main
	rm -rf "$(TEST_CLASSES)"
	mkdir -p "$(TEST_CLASSES)"
	$(JAVAC) $(JAVA_FLAGS) -cp "$(MAIN_CLASSES)" -d "$(TEST_CLASSES)" $(TEST_SOURCES)

build: compile-main
	mkdir -p "$(BIN_DIR)"
	$(JAR) --create --file "$(BIN_DIR)/liff.jar" --main-class liff.cli.Main -C "$(MAIN_CLASSES)" .
	cp "$(MAKEFILE_DIR)src/launcher/liff" "$(BIN_DIR)/liff"
	chmod 755 "$(BIN_DIR)/liff"

test: check-generated compile-test
	$(JAVA) -ea -Dliff.repoRoot="$(REPO_ROOT)" -cp "$(MAIN_CLASSES):$(TEST_CLASSES)" liff.core.CoreConformanceTest
	$(JAVA) -ea -Dliff.repoRoot="$(REPO_ROOT)" -cp "$(MAIN_CLASSES):$(TEST_CLASSES)" liff.cli.MainTest

lint: check-generated
	cd "$(REPO_ROOT)" && python3 -B -c 'from pathlib import Path; paths=list(Path("impl/java/src").rglob("*.java")); bad=[f"{p}:{n}" for p in paths for n,line in enumerate(p.read_text(encoding="utf-8").splitlines(),1) if line.rstrip()!=line or "\t" in line]; assert not bad, "Java whitespace errors: " + ", ".join(bad)'

check: test lint

clean:
	rm -rf "$(BUILD_DIR)" "$(BIN_DIR)"
