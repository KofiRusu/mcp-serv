#!/bin/bash
# =============================================================================
# ChatOS v2.0 - Common Transform Functions
# =============================================================================
# Shared utility functions used by OS-specific transform scripts.
# This file is sourced by translate_patch.sh and individual OS transforms.
# =============================================================================

# =============================================================================
# Utility Functions
# =============================================================================

# Log function (uses parent script's log functions if available)
_log() {
    local level="$1"
    local message="$2"
    
    case "$level" in
        info)    echo -e "\033[0;34m[TRANSFORM]\033[0m $message" ;;
        success) echo -e "\033[0;32m[TRANSFORM]\033[0m $message" ;;
        warning) echo -e "\033[1;33m[TRANSFORM]\033[0m $message" ;;
        error)   echo -e "\033[0;31m[TRANSFORM]\033[0m $message" ;;
    esac
}

# =============================================================================
# File Manipulation
# =============================================================================

# Replace a value in a config file
# Usage: replace_config_value <file> <key> <new_value>
replace_config_value() {
    local file="$1"
    local key="$2"
    local new_value="$3"
    
    if [ ! -f "$file" ]; then
        _log warning "File not found: $file"
        return 1
    fi
    
    # Handle different config formats
    if grep -q "^${key}=" "$file" 2>/dev/null; then
        # KEY=value format
        sed -i.bak "s|^${key}=.*|${key}=${new_value}|" "$file"
        rm -f "${file}.bak"
        return 0
    elif grep -q "^${key}:" "$file" 2>/dev/null; then
        # KEY: value format (YAML)
        sed -i.bak "s|^${key}:.*|${key}: ${new_value}|" "$file"
        rm -f "${file}.bak"
        return 0
    fi
    
    return 1
}

# Append a line to a file if it doesn't exist
# Usage: append_if_missing <file> <line>
append_if_missing() {
    local file="$1"
    local line="$2"
    
    if [ ! -f "$file" ]; then
        echo "$line" > "$file"
        return 0
    fi
    
    if ! grep -qF "$line" "$file" 2>/dev/null; then
        echo "$line" >> "$file"
        return 0
    fi
    
    return 1
}

# Comment out a line in a file
# Usage: comment_line <file> <pattern>
comment_line() {
    local file="$1"
    local pattern="$2"
    
    if [ ! -f "$file" ]; then
        return 1
    fi
    
    sed -i.bak "s|^${pattern}|# ${pattern}|" "$file"
    rm -f "${file}.bak"
}

# Uncomment a line in a file
# Usage: uncomment_line <file> <pattern>
uncomment_line() {
    local file="$1"
    local pattern="$2"
    
    if [ ! -f "$file" ]; then
        return 1
    fi
    
    sed -i.bak "s|^# *${pattern}|${pattern}|" "$file"
    rm -f "${file}.bak"
}

# =============================================================================
# Environment Detection
# =============================================================================

# Check if running in Docker
is_docker() {
    [ -f "/.dockerenv" ] || grep -q docker /proc/1/cgroup 2>/dev/null
}

# Check if GPU is available (NVIDIA on Linux)
has_nvidia_gpu() {
    command -v nvidia-smi &> /dev/null && nvidia-smi &> /dev/null
}

# Check if MPS is available (Apple Silicon)
has_mps() {
    [ "$(uname -s)" = "Darwin" ] && [ "$(uname -m)" = "arm64" ]
}

# Get Python version
get_python_version() {
    python3 --version 2>&1 | cut -d' ' -f2
}

# Get Node version
get_node_version() {
    node --version 2>&1 | tr -d 'v'
}

# =============================================================================
# Path Utilities
# =============================================================================

# Expand ~ in path to full home directory
expand_path() {
    local path="$1"
    echo "${path/#\~/$HOME}"
}

# Get relative path from repo root
relative_to_repo() {
    local full_path="$1"
    local repo_root="$2"
    
    echo "${full_path#$repo_root/}"
}

# =============================================================================
# Validation Helpers
# =============================================================================

# Check if a port is in use
port_in_use() {
    local port="$1"
    
    if command -v lsof &> /dev/null; then
        lsof -i ":$port" &> /dev/null
    elif command -v netstat &> /dev/null; then
        netstat -tuln | grep -q ":$port "
    elif command -v ss &> /dev/null; then
        ss -tuln | grep -q ":$port "
    else
        return 1
    fi
}

# Wait for a port to become available
wait_for_port() {
    local port="$1"
    local timeout="${2:-30}"
    local count=0
    
    while ! port_in_use "$port"; do
        sleep 1
        ((count++))
        if [ $count -ge $timeout ]; then
            return 1
        fi
    done
    
    return 0
}

# Wait for HTTP endpoint to respond
wait_for_http() {
    local url="$1"
    local timeout="${2:-30}"
    local count=0
    
    while ! curl -s "$url" &> /dev/null; do
        sleep 1
        ((count++))
        if [ $count -ge $timeout ]; then
            return 1
        fi
    done
    
    return 0
}

# =============================================================================
# Exports
# =============================================================================

export -f _log
export -f replace_config_value
export -f append_if_missing
export -f comment_line
export -f uncomment_line
export -f is_docker
export -f has_nvidia_gpu
export -f has_mps
export -f get_python_version
export -f get_node_version
export -f expand_path
export -f relative_to_repo
export -f port_in_use
export -f wait_for_port
export -f wait_for_http

