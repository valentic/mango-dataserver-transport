export LOCAL_DIR = $(DATA_TRANSPORT_PATH)/.local
export UV_CACHE_DIR = $(LOCAL_DIR)/cache
export UV_PYTHON_INSTALL_DIR = $(LOCAL_DIR)/python
export UV_PYTHON_BIN_DIR = $(LOCAL_DIR)/bin
export UV_VENV_CLEAR = 1
export UV_PROJECT_ENVIRONMENT = $(DATA_TRANSPORT_PATH)/.venv
export PATH := $(UV_PYTHON_BIN_DIR):$(PATH)

.PHONY:	help setup

help:
	@echo "  setup  Setup environment"
	@echo "  clean  Remove cache, venv"
	@echo "  help   List makefile target commands"

setup:
	@mkdir -p $(UV_CACHE_DIR) 
	@mkdir -p $(UV_PYTHON_INSTALL_DIR) 
	@mkdir -p $(UV_PYTHON_BIN_DIR)

	@uv python install 
	@uv venv 
	@uv sync
	@restorecon -r /opt/transport/.venv/bin	
	@restorecon -r /opt/transport/.local

clean:
	@rm -rf $(LOCAL_DIR)
	@rm -rf $(UV_PROJECT_ENVIRONMENT)
