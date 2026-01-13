#!/usr/bin/env bash
#
# Environment configuration validation script
# Checks for weak passwords, missing required variables, and security issues
#

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Track errors and warnings
ERRORS=0
WARNINGS=0

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    ((ERRORS++))
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
    ((WARNINGS++))
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

# Weak/default values to check for
WEAK_PASSWORDS=(
    "admin"
    "password"
    "changeme"
    "change-me"
    "change-this"
    "default"
    "test"
    "123456"
)

WEAK_SECRETS=(
    "sk-1234567890abcdef"
    "change-me-generate-with-openssl-rand-hex-32"
)

check_env_file() {
    local env_file="$1"
    local file_type="${2:-production}"
    
    echo ""
    echo "=== Checking $env_file ($file_type) ==="
    echo ""
    
    if [[ ! -f "$env_file" ]]; then
        if [[ "$file_type" == "production" ]]; then
            log_error "File $env_file not found"
        else
            log_warning "Example file $env_file not found"
        fi
        return
    fi
    
    # Check for weak passwords
    for weak_pass in "${WEAK_PASSWORDS[@]}"; do
        if grep -qi "password.*=.*${weak_pass}" "$env_file"; then
            if [[ "$file_type" == "production" ]]; then
                log_error "Weak password detected in $env_file: contains '$weak_pass'"
            else
                log_warning "Example file contains weak password placeholder: '$weak_pass'"
            fi
        fi
    done
    
    # Check for weak secrets
    for weak_secret in "${WEAK_SECRETS[@]}"; do
        if grep -q "$weak_secret" "$env_file"; then
            if [[ "$file_type" == "production" ]]; then
                log_error "Default secret key detected in $env_file"
            fi
        fi
    done
    
    # Check for CORS wildcard in production
    if [[ "$file_type" == "production" ]] && grep -q "CORS_ALLOW_ORIGIN=\*" "$env_file"; then
        log_warning "CORS wildcard (*) detected - not recommended for production"
    fi
    
    # Check required variables for production files
    if [[ "$file_type" == "production" ]]; then
        local required_vars=(
            "WEBUI_SECRET_KEY"
            "DATA_PATH"
        )
        
        for var in "${required_vars[@]}"; do
            if ! grep -q "^${var}=" "$env_file"; then
                log_error "Required variable $var not found in $env_file"
            fi
        done
        
        # Check secret key length
        if grep -q "^WEBUI_SECRET_KEY=" "$env_file"; then
            local secret_key
            secret_key=$(grep "^WEBUI_SECRET_KEY=" "$env_file" | cut -d'=' -f2-)
            if [[ ${#secret_key} -lt 32 ]]; then
                log_error "WEBUI_SECRET_KEY is too short (< 32 characters)"
            elif [[ "$secret_key" == *"change"* ]] || [[ "$secret_key" == *"example"* ]]; then
                log_error "WEBUI_SECRET_KEY appears to be a placeholder value"
            else
                log_success "WEBUI_SECRET_KEY has adequate length"
            fi
        fi
    fi
    
    # Check for commented-out security settings
    if grep -E "^#.*HTTPS|^#.*SSL|^#.*TLS" "$env_file" > /dev/null; then
        log_warning "HTTPS/SSL/TLS settings are commented out"
    fi
    
    # Check for debug mode in production
    if [[ "$file_type" == "production" ]]; then
        if grep -Eq "^DEBUG=true|^DEBUG=1" "$env_file"; then
            log_warning "DEBUG mode is enabled - should be disabled in production"
        fi
    fi
    
    # Check file permissions
    if [[ -f "$env_file" ]]; then
        local perms
        perms=$(stat -c "%a" "$env_file" 2>/dev/null || stat -f "%A" "$env_file" 2>/dev/null || echo "unknown")
        if [[ "$perms" != "600" ]] && [[ "$perms" != "400" ]]; then
            log_warning "File permissions for $env_file are $perms (should be 600 or 400)"
        else
            log_success "File permissions are secure ($perms)"
        fi
    fi
}

generate_secure_secret() {
    if command -v openssl > /dev/null; then
        openssl rand -hex 32
    elif command -v python3 > /dev/null; then
        python3 -c "import secrets; print(secrets.token_hex(32))"
    else
        echo "ERROR: Cannot generate secure secret - openssl or python3 required"
        return 1
    fi
}

check_docker_compose_security() {
    echo ""
    echo "=== Checking Docker Compose Security ==="
    echo ""
    
    local compose_files=(
        "server/docker-compose.yml"
        "server/docker-compose.multimodal.yml"
        "gpu-worker/docker-compose.yml"
    )
    
    for compose_file in "${compose_files[@]}"; do
        if [[ ! -f "$compose_file" ]]; then
            log_warning "Compose file not found: $compose_file"
            continue
        fi
        
        # Check for exposed ports
        if grep -q "0.0.0.0:" "$compose_file"; then
            log_warning "$compose_file: Services exposed on 0.0.0.0 (all interfaces)"
        fi
        
        # Check for privileged containers
        if grep -q "privileged: true" "$compose_file"; then
            log_warning "$compose_file: Privileged containers detected"
        fi
        
        # Check for host network mode
        if grep -q "network_mode: host" "$compose_file"; then
            log_warning "$compose_file: Host network mode detected"
        fi
    done
}

main() {
    echo "╔════════════════════════════════════════════════════════╗"
    echo "║   Self-Hosted AI Stack - Security Validation          ║"
    echo "╚════════════════════════════════════════════════════════╝"
    
    # Check production .env files
    check_env_file "server/.env" "production"
    check_env_file "gpu-worker/.env" "production"
    
    # Check example files
    check_env_file "server/.env.example" "example"
    check_env_file "server/.env.multimodal.example" "example"
    check_env_file "gpu-worker/.env.example" "example"
    
    # Check Docker Compose security
    check_docker_compose_security
    
    # Summary
    echo ""
    echo "═══════════════════════════════════════════════════════"
    echo " Validation Summary"
    echo "═══════════════════════════════════════════════════════"
    
    if [[ $ERRORS -eq 0 ]] && [[ $WARNINGS -eq 0 ]]; then
        echo -e "${GREEN}✓ All checks passed!${NC}"
        exit 0
    elif [[ $ERRORS -eq 0 ]]; then
        echo -e "${YELLOW}⚠ $WARNINGS warning(s) found${NC}"
        echo ""
        echo "Review warnings above. Consider fixing before deployment."
        exit 0
    else
        echo -e "${RED}✗ $ERRORS error(s) and $WARNINGS warning(s) found${NC}"
        echo ""
        echo "Fix errors above before deploying to production."
        echo ""
        echo "Quick fixes:"
        echo "  1. Generate secure secrets:"
        echo "     WEBUI_SECRET_KEY=\$(openssl rand -hex 32)"
        echo "     LITELLM_MASTER_KEY=\$(openssl rand -hex 32)"
        echo "  2. Set strong passwords for all services"
        echo "  3. Restrict CORS to specific domains"
        echo "  4. Set proper file permissions: chmod 600 server/.env"
        exit 1
    fi
}

main "$@"
