#!/bin/bash
# Run AEGIS with qwen2.5-coder:7b model
export OLLAMA_MODEL=qwen2.5-coder:7b
export AGENT_RCA_MODEL=qwen2.5-coder:7b
export AGENT_SOLUTION_MODEL=qwen2.5-coder:7b
export AGENT_VERIFIER_MODEL=qwen2.5-coder:7b
source $HOME/.local/bin/env
uv run aegis "$@"

