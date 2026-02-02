.PHONY: all
all: backend.test.unit backend.code-quality frontend.ui.build docker.build ## Build all components

# Includes
include cmd/build/utils.mk
include cmd/build/code-quality.mk
include cmd/build/build.mk
include cmd/build/docker.mk
include cmd/local-setup/local.mk
include cmd/local-setup/docker.mk

















