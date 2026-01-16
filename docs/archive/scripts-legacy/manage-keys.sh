#!/usr/bin/env bash
# API Key Management CLI for Agent Server
# Handles generation, rotation, revocation, and listing of API keys
# with 90-day auto-rotation support and Prometheus metrics

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Default values
AGENT_SERVER_URL="${AGENT_SERVER_URL:-http://localhost:8080}"
DATABASE_URL="${DATABASE_URL:-postgresql://agents:agents@localhost:5432/agents}"
KEY_ROTATION_DAYS="${KEY_ROTATION_DAYS:-90}"
KEY_WARNING_DAYS="${KEY_WARNING_DAYS:-80}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

# Help function
show_help() {
    cat << EOF
API Key Management CLI

Usage: $(basename "$0") <command> [options]

Commands:
  generate        Generate a new API key
  rotate          Rotate an existing API key
  revoke          Revoke an API key
  list            List all API keys
  check           Check for keys needing rotation
  export-metrics  Export Prometheus metrics
  cleanup         Remove expired/revoked keys from database

Options:
  -n, --name        Key name/description
  -k, --key-id      Key ID for rotate/revoke operations
  -e, --expires     Expiration days (default: $KEY_ROTATION_DAYS)
  -t, --tier        API tier: free, standard, premium (default: standard)
  -l, --rate-limit  Rate limit per minute (default: 60)
  -q, --quiet       Suppress informational output
  -h, --help        Show this help message

Environment Variables:
  AGENT_SERVER_URL   Agent server base URL (default: http://localhost:8080)
  DATABASE_URL       PostgreSQL connection URL
  KEY_ROTATION_DAYS  Days until key expiration (default: 90)
  KEY_WARNING_DAYS   Days before expiration to warn (default: 80)

Examples:
  $(basename "$0") generate --name "production-api" --tier premium
  $(basename "$0") rotate --key-id abc123
  $(basename "$0") revoke --key-id abc123
  $(basename "$0") list
  $(basename "$0") check
  $(basename "$0") export-metrics > /var/lib/prometheus/keys.prom

EOF
}

# Generate cryptographically secure API key
generate_key_value() {
    # Generate 32 bytes of random data, base64 encode, make URL-safe
    python3 -c "import secrets; import base64; print('sk_' + base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip('='))"
}

# Hash key for storage
hash_key() {
    local key="$1"
    echo -n "$key" | sha256sum | cut -d' ' -f1
}

# Generate a new API key
cmd_generate() {
    local name=""
    local tier="standard"
    local rate_limit="60"
    local expires_days="$KEY_ROTATION_DAYS"
    local quiet=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            -n|--name) name="$2"; shift 2 ;;
            -t|--tier) tier="$2"; shift 2 ;;
            -l|--rate-limit) rate_limit="$2"; shift 2 ;;
            -e|--expires) expires_days="$2"; shift 2 ;;
            -q|--quiet) quiet=true; shift ;;
            *) shift ;;
        esac
    done
    
    if [[ -z "$name" ]]; then
        log_error "Key name is required. Use --name <name>"
        exit 1
    fi
    
    # Validate tier
    if [[ ! "$tier" =~ ^(free|standard|premium)$ ]]; then
        log_error "Invalid tier. Must be: free, standard, or premium"
        exit 1
    fi
    
    # Generate key
    local key_value
    key_value=$(generate_key_value)
    local key_hash
    key_hash=$(hash_key "$key_value")
    local key_prefix="${key_value:0:12}"
    
    # Calculate expiration
    local expires_at
    expires_at=$(date -d "+${expires_days} days" -Iseconds)
    
    if [[ "$quiet" == false ]]; then
        log_info "Generating API key: $name"
    fi
    
    # Store in database via psql or API
    if command -v psql &> /dev/null && [[ -n "${DATABASE_URL:-}" ]]; then
        psql "$DATABASE_URL" -q << EOF
INSERT INTO api_keys (
    key_hash,
    key_prefix,
    name,
    tier,
    rate_limit_per_minute,
    expires_at,
    created_at,
    is_active
) VALUES (
    '$key_hash',
    '$key_prefix',
    '$name',
    '$tier',
    $rate_limit,
    '$expires_at',
    NOW(),
    true
);
EOF
    else
        # Try via API
        local response
        response=$(curl -s -X POST "${AGENT_SERVER_URL}/internal/keys" \
            -H "Content-Type: application/json" \
            -H "X-Internal-Secret: ${INTERNAL_SECRET:-}" \
            -d "{
                \"name\": \"$name\",
                \"tier\": \"$tier\",
                \"rate_limit_per_minute\": $rate_limit,
                \"expires_days\": $expires_days
            }" 2>/dev/null || echo "")
        
        if [[ -z "$response" ]]; then
            log_error "Could not store key. Ensure DATABASE_URL is set or agent server is running."
            exit 1
        fi
    fi
    
    if [[ "$quiet" == false ]]; then
        log_success "API key generated successfully"
        echo ""
        echo "┌────────────────────────────────────────────────────────────────────────┐"
        echo "│ IMPORTANT: Save this key now. It cannot be retrieved later.           │"
        echo "├────────────────────────────────────────────────────────────────────────┤"
        printf "│ %-70s │\n" "Key: $key_value"
        printf "│ %-70s │\n" "Name: $name"
        printf "│ %-70s │\n" "Tier: $tier"
        printf "│ %-70s │\n" "Rate Limit: $rate_limit/min"
        printf "│ %-70s │\n" "Expires: $expires_at"
        echo "└────────────────────────────────────────────────────────────────────────┘"
    else
        echo "$key_value"
    fi
}

# Rotate an existing key
cmd_rotate() {
    local key_id=""
    local quiet=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            -k|--key-id) key_id="$2"; shift 2 ;;
            -q|--quiet) quiet=true; shift ;;
            *) shift ;;
        esac
    done
    
    if [[ -z "$key_id" ]]; then
        log_error "Key ID is required. Use --key-id <id>"
        exit 1
    fi
    
    if [[ "$quiet" == false ]]; then
        log_info "Rotating key: $key_id"
    fi
    
    # Get existing key info
    local key_info
    if command -v psql &> /dev/null && [[ -n "${DATABASE_URL:-}" ]]; then
        key_info=$(psql "$DATABASE_URL" -t -A -c "SELECT name, tier, rate_limit_per_minute FROM api_keys WHERE key_prefix = '$key_id' OR id::text = '$key_id'")
    fi
    
    if [[ -z "$key_info" ]]; then
        log_error "Key not found: $key_id"
        exit 1
    fi
    
    # Parse info
    local name tier rate_limit
    IFS='|' read -r name tier rate_limit <<< "$key_info"
    
    # Generate new key
    local new_key
    new_key=$(generate_key_value)
    local new_hash
    new_hash=$(hash_key "$new_key")
    local new_prefix="${new_key:0:12}"
    local expires_at
    expires_at=$(date -d "+${KEY_ROTATION_DAYS} days" -Iseconds)
    
    # Update in database
    if command -v psql &> /dev/null && [[ -n "${DATABASE_URL:-}" ]]; then
        psql "$DATABASE_URL" -q << EOF
UPDATE api_keys SET
    key_hash = '$new_hash',
    key_prefix = '$new_prefix',
    expires_at = '$expires_at',
    rotated_at = NOW()
WHERE key_prefix = '$key_id' OR id::text = '$key_id';
EOF
    fi
    
    if [[ "$quiet" == false ]]; then
        log_success "Key rotated successfully"
        echo ""
        echo "┌────────────────────────────────────────────────────────────────────────┐"
        echo "│ IMPORTANT: Update your applications with the new key.                 │"
        echo "├────────────────────────────────────────────────────────────────────────┤"
        printf "│ %-70s │\n" "New Key: $new_key"
        printf "│ %-70s │\n" "Name: $name"
        printf "│ %-70s │\n" "Expires: $expires_at"
        echo "└────────────────────────────────────────────────────────────────────────┘"
    else
        echo "$new_key"
    fi
}

# Revoke a key
cmd_revoke() {
    local key_id=""
    local quiet=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            -k|--key-id) key_id="$2"; shift 2 ;;
            -q|--quiet) quiet=true; shift ;;
            *) shift ;;
        esac
    done
    
    if [[ -z "$key_id" ]]; then
        log_error "Key ID is required. Use --key-id <id>"
        exit 1
    fi
    
    if [[ "$quiet" == false ]]; then
        log_info "Revoking key: $key_id"
    fi
    
    if command -v psql &> /dev/null && [[ -n "${DATABASE_URL:-}" ]]; then
        local result
        result=$(psql "$DATABASE_URL" -t -A -c "
            UPDATE api_keys 
            SET is_active = false, revoked_at = NOW() 
            WHERE (key_prefix = '$key_id' OR id::text = '$key_id') AND is_active = true
            RETURNING name;
        ")
        
        if [[ -z "$result" ]]; then
            log_error "Key not found or already revoked: $key_id"
            exit 1
        fi
        
        if [[ "$quiet" == false ]]; then
            log_success "Key revoked: $result"
        fi
    else
        log_error "DATABASE_URL not configured"
        exit 1
    fi
}

# List all keys
cmd_list() {
    local quiet=false
    local format="table"
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            -q|--quiet) quiet=true; shift ;;
            --json) format="json"; shift ;;
            *) shift ;;
        esac
    done
    
    if [[ "$quiet" == false ]]; then
        log_info "Listing API keys"
    fi
    
    if command -v psql &> /dev/null && [[ -n "${DATABASE_URL:-}" ]]; then
        if [[ "$format" == "json" ]]; then
            psql "$DATABASE_URL" -t -A -c "
                SELECT json_agg(row_to_json(t))
                FROM (
                    SELECT 
                        key_prefix,
                        name,
                        tier,
                        rate_limit_per_minute,
                        is_active,
                        created_at,
                        expires_at,
                        EXTRACT(DAY FROM (expires_at - NOW())) as days_until_expiry
                    FROM api_keys
                    ORDER BY created_at DESC
                ) t;
            "
        else
            echo ""
            echo "┌──────────────┬────────────────────────┬──────────┬────────┬────────────┬───────────────┐"
            echo "│ Key Prefix   │ Name                   │ Tier     │ Active │ Rate Limit │ Days to Expiry│"
            echo "├──────────────┼────────────────────────┼──────────┼────────┼────────────┼───────────────┤"
            
            psql "$DATABASE_URL" -t -A -c "
                SELECT 
                    key_prefix,
                    SUBSTRING(name, 1, 22),
                    tier,
                    CASE WHEN is_active THEN 'Yes' ELSE 'No' END,
                    rate_limit_per_minute,
                    COALESCE(EXTRACT(DAY FROM (expires_at - NOW()))::int::text, 'N/A')
                FROM api_keys
                ORDER BY created_at DESC;
            " | while IFS='|' read -r prefix name tier active rate_limit days; do
                printf "│ %-12s │ %-22s │ %-8s │ %-6s │ %-10s │ %-13s │\n" \
                    "$prefix" "$name" "$tier" "$active" "${rate_limit}/min" "$days"
            done
            
            echo "└──────────────┴────────────────────────┴──────────┴────────┴────────────┴───────────────┘"
        fi
    else
        log_error "DATABASE_URL not configured"
        exit 1
    fi
}

# Check for keys needing rotation
cmd_check() {
    local quiet=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            -q|--quiet) quiet=true; shift ;;
            *) shift ;;
        esac
    done
    
    if [[ "$quiet" == false ]]; then
        log_info "Checking keys for rotation (warning at $KEY_WARNING_DAYS days)"
    fi
    
    if command -v psql &> /dev/null && [[ -n "${DATABASE_URL:-}" ]]; then
        local expiring_soon
        expiring_soon=$(psql "$DATABASE_URL" -t -A -c "
            SELECT COUNT(*) FROM api_keys 
            WHERE is_active = true 
            AND expires_at <= NOW() + INTERVAL '$KEY_WARNING_DAYS days';
        ")
        
        local expired
        expired=$(psql "$DATABASE_URL" -t -A -c "
            SELECT COUNT(*) FROM api_keys 
            WHERE is_active = true 
            AND expires_at <= NOW();
        ")
        
        if [[ "$quiet" == false ]]; then
            echo ""
            if [[ "$expired" -gt 0 ]]; then
                log_error "Expired keys: $expired"
                psql "$DATABASE_URL" -t -A -c "
                    SELECT key_prefix, name 
                    FROM api_keys 
                    WHERE is_active = true AND expires_at <= NOW();
                " | while IFS='|' read -r prefix name; do
                    echo "  - $prefix ($name)"
                done
            else
                log_success "No expired keys"
            fi
            
            echo ""
            if [[ "$expiring_soon" -gt 0 ]]; then
                log_warning "Keys expiring within $KEY_WARNING_DAYS days: $expiring_soon"
                psql "$DATABASE_URL" -t -A -c "
                    SELECT key_prefix, name, EXTRACT(DAY FROM (expires_at - NOW()))::int
                    FROM api_keys 
                    WHERE is_active = true 
                    AND expires_at > NOW()
                    AND expires_at <= NOW() + INTERVAL '$KEY_WARNING_DAYS days'
                    ORDER BY expires_at;
                " | while IFS='|' read -r prefix name days; do
                    echo "  - $prefix ($name) - $days days remaining"
                done
            else
                log_success "No keys expiring soon"
            fi
        fi
        
        # Return exit code based on status
        if [[ "$expired" -gt 0 ]]; then
            exit 2
        elif [[ "$expiring_soon" -gt 0 ]]; then
            exit 1
        else
            exit 0
        fi
    else
        log_error "DATABASE_URL not configured"
        exit 1
    fi
}

# Export Prometheus metrics
cmd_export_metrics() {
    if ! command -v psql &> /dev/null || [[ -z "${DATABASE_URL:-}" ]]; then
        log_error "DATABASE_URL not configured"
        exit 1
    fi
    
    # Header
    echo "# HELP api_keys_total Total number of API keys"
    echo "# TYPE api_keys_total gauge"
    
    local total
    total=$(psql "$DATABASE_URL" -t -A -c "SELECT COUNT(*) FROM api_keys;")
    echo "api_keys_total $total"
    
    echo ""
    echo "# HELP api_keys_active Number of active API keys"
    echo "# TYPE api_keys_active gauge"
    
    local active
    active=$(psql "$DATABASE_URL" -t -A -c "SELECT COUNT(*) FROM api_keys WHERE is_active = true;")
    echo "api_keys_active $active"
    
    echo ""
    echo "# HELP api_keys_expired Number of expired but not revoked keys"
    echo "# TYPE api_keys_expired gauge"
    
    local expired
    expired=$(psql "$DATABASE_URL" -t -A -c "
        SELECT COUNT(*) FROM api_keys 
        WHERE is_active = true AND expires_at <= NOW();
    ")
    echo "api_keys_expired $expired"
    
    echo ""
    echo "# HELP api_keys_expiring_soon Keys expiring within warning period"
    echo "# TYPE api_keys_expiring_soon gauge"
    
    local expiring
    expiring=$(psql "$DATABASE_URL" -t -A -c "
        SELECT COUNT(*) FROM api_keys 
        WHERE is_active = true 
        AND expires_at > NOW()
        AND expires_at <= NOW() + INTERVAL '$KEY_WARNING_DAYS days';
    ")
    echo "api_keys_expiring_soon $expiring"
    
    echo ""
    echo "# HELP api_keys_by_tier Number of keys by tier"
    echo "# TYPE api_keys_by_tier gauge"
    
    psql "$DATABASE_URL" -t -A -c "
        SELECT tier, COUNT(*) FROM api_keys 
        WHERE is_active = true 
        GROUP BY tier;
    " | while IFS='|' read -r tier count; do
        echo "api_keys_by_tier{tier=\"$tier\"} $count"
    done
    
    echo ""
    echo "# HELP api_key_age_days Age of each active key in days"
    echo "# TYPE api_key_age_days gauge"
    
    psql "$DATABASE_URL" -t -A -c "
        SELECT key_prefix, EXTRACT(DAY FROM (NOW() - created_at))::int
        FROM api_keys 
        WHERE is_active = true;
    " | while IFS='|' read -r prefix age; do
        echo "api_key_age_days{key_prefix=\"$prefix\"} $age"
    done
    
    echo ""
    echo "# HELP api_key_days_until_expiry Days until key expires"
    echo "# TYPE api_key_days_until_expiry gauge"
    
    psql "$DATABASE_URL" -t -A -c "
        SELECT key_prefix, GREATEST(EXTRACT(DAY FROM (expires_at - NOW()))::int, 0)
        FROM api_keys 
        WHERE is_active = true;
    " | while IFS='|' read -r prefix days; do
        echo "api_key_days_until_expiry{key_prefix=\"$prefix\"} $days"
    done
}

# Cleanup old/revoked keys
cmd_cleanup() {
    local days=30
    local quiet=false
    local dry_run=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            -d|--days) days="$2"; shift 2 ;;
            -q|--quiet) quiet=true; shift ;;
            --dry-run) dry_run=true; shift ;;
            *) shift ;;
        esac
    done
    
    if [[ "$quiet" == false ]]; then
        log_info "Cleaning up keys revoked/expired more than $days days ago"
    fi
    
    if command -v psql &> /dev/null && [[ -n "${DATABASE_URL:-}" ]]; then
        local to_delete
        to_delete=$(psql "$DATABASE_URL" -t -A -c "
            SELECT COUNT(*) FROM api_keys 
            WHERE (
                (is_active = false AND revoked_at <= NOW() - INTERVAL '$days days')
                OR (expires_at <= NOW() - INTERVAL '$days days')
            );
        ")
        
        if [[ "$quiet" == false ]]; then
            echo "Keys to cleanup: $to_delete"
        fi
        
        if [[ "$dry_run" == true ]]; then
            log_info "Dry run - no keys deleted"
        elif [[ "$to_delete" -gt 0 ]]; then
            psql "$DATABASE_URL" -q -c "
                DELETE FROM api_keys 
                WHERE (
                    (is_active = false AND revoked_at <= NOW() - INTERVAL '$days days')
                    OR (expires_at <= NOW() - INTERVAL '$days days')
                );
            "
            log_success "Cleaned up $to_delete keys"
        fi
    else
        log_error "DATABASE_URL not configured"
        exit 1
    fi
}

# Auto-rotate expiring keys
cmd_auto_rotate() {
    local quiet=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            -q|--quiet) quiet=true; shift ;;
            *) shift ;;
        esac
    done
    
    if [[ "$quiet" == false ]]; then
        log_info "Auto-rotating expired keys"
    fi
    
    if command -v psql &> /dev/null && [[ -n "${DATABASE_URL:-}" ]]; then
        # Get keys that have expired
        local expired_keys
        expired_keys=$(psql "$DATABASE_URL" -t -A -c "
            SELECT key_prefix FROM api_keys 
            WHERE is_active = true AND expires_at <= NOW();
        ")
        
        if [[ -z "$expired_keys" ]]; then
            if [[ "$quiet" == false ]]; then
                log_success "No keys need rotation"
            fi
            return 0
        fi
        
        echo "$expired_keys" | while read -r key_id; do
            if [[ -n "$key_id" ]]; then
                if [[ "$quiet" == false ]]; then
                    log_info "Rotating expired key: $key_id"
                fi
                cmd_rotate --key-id "$key_id" --quiet
            fi
        done
        
        if [[ "$quiet" == false ]]; then
            log_success "Auto-rotation complete"
        fi
    else
        log_error "DATABASE_URL not configured"
        exit 1
    fi
}

# Main entry point
main() {
    if [[ $# -eq 0 ]]; then
        show_help
        exit 0
    fi
    
    local command="$1"
    shift
    
    case "$command" in
        generate)
            cmd_generate "$@"
            ;;
        rotate)
            cmd_rotate "$@"
            ;;
        revoke)
            cmd_revoke "$@"
            ;;
        list)
            cmd_list "$@"
            ;;
        check)
            cmd_check "$@"
            ;;
        export-metrics)
            cmd_export_metrics
            ;;
        cleanup)
            cmd_cleanup "$@"
            ;;
        auto-rotate)
            cmd_auto_rotate "$@"
            ;;
        -h|--help|help)
            show_help
            ;;
        *)
            log_error "Unknown command: $command"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

main "$@"
