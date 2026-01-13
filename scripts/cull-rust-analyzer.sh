#!/bin/bash

# Script to cull rust-analyzer instances, keeping only the ones for self-hosted-ai and context-mcp workspaces

CURRENT_DIR=$(pwd)
KEEP_DIRS=(
    "/home/kang/Documents/projects/github/self-hosted-ai"
    "/home/kang/Documents/projects/2026/mcp/context-mcp"
)

# Find all rust-analyzer main processes (not proc-macro-srv)
RUST_ANALYZER_PIDS=$(pgrep -f "rust-analyzer" | xargs ps -o pid,cmd -p 2>/dev/null | grep -v proc-macro-srv | awk '{print $1}')

for PID in $RUST_ANALYZER_PIDS; do
    if [ -n "$PID" ] && [ "$PID" != "$$" ]; then
        PROCESS_CWD=$(pwdx $PID 2>/dev/null | awk '{print $2}')
        KEEP=false
        for DIR in "${KEEP_DIRS[@]}"; do
            if [ "$PROCESS_CWD" = "$DIR" ]; then
                KEEP=true
                break
            fi
        done
        if [ "$KEEP" = false ]; then
            echo "Killing rust-analyzer PID $PID in $PROCESS_CWD"
            kill -9 $PID 2>/dev/null
        else
            echo "Keeping rust-analyzer PID $PID in $PROCESS_CWD"
        fi
    fi
done