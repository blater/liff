ROOT_DIR := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))

.PHONY: tidy

tidy:
	rm -rf "$(ROOT_DIR)internal" "$(ROOT_DIR)tmp" "$(ROOT_DIR)generated"
	rm -rf "$(ROOT_DIR)impl/rust/target"
	rm -rf "$(ROOT_DIR)impl/zig/.zig-cache" "$(ROOT_DIR)impl/zig/.zig-global-cache" "$(ROOT_DIR)impl/zig/zig-out"
	rm -rf "$(ROOT_DIR)impl/java/build"
	rm -rf "$(ROOT_DIR)impl/typescript/build"
	rm -rf "$(ROOT_DIR)impl/c/build"
	find "$(ROOT_DIR)" -type d -name __pycache__ -prune -exec rm -rf {} +
	find "$(ROOT_DIR)" -type f \( -name '*.pyc' -o -name '*.pyo' -o -name '.DS_Store' \) -delete
