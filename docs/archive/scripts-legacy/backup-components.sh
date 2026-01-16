#!/usr/bin/env bash
# backup-components.sh - Targeted backup script for individual components
# Supports PostgreSQL, Qdrant, OpenWebUI, and config exports
# Local retention: 7 daily, 4 weekly with optional remote archival

set -euo pipefail

# =============================================================================
# Configuration
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Default paths
BACKUP_ROOT="${BACKUP_ROOT:-/data/backups}"
LOCAL_RETENTION_DAILY="${LOCAL_RETENTION_DAILY:-7}"
LOCAL_RETENTION_WEEKLY="${LOCAL_RETENTION_WEEKLY:-4}"

# Remote archival (optional)
REMOTE_ENABLED="${REMOTE_ENABLED:-false}"
REMOTE_TYPE="${REMOTE_TYPE:-s3}"  # s3, gcs
REMOTE_BUCKET="${REMOTE_BUCKET:-}"
REMOTE_PREFIX="${REMOTE_PREFIX:-self-hosted-ai/backups}"

# Service endpoints
POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_USER="${POSTGRES_USER:-litellm}"
POSTGRES_DB="${POSTGRES_DB:-litellm}"
QDRANT_HOST="${QDRANT_HOST:-localhost}"
QDRANT_PORT="${QDRANT_PORT:-6333}"
OPENWEBUI_DATA="${OPENWEBUI_DATA:-/data/open-webui}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# =============================================================================
# Utility Functions
# =============================================================================

log_info() { echo -e "${BLUE}[INFO]${NC} $*"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $*"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }

ensure_dir() {
    local dir="$1"
    if [[ ! -d "$dir" ]]; then
        mkdir -p "$dir"
        log_info "Created directory: $dir"
    fi
}

get_timestamp() {
    date +"%Y%m%d_%H%M%S"
}

get_date() {
    date +"%Y%m%d"
}

get_day_of_week() {
    date +"%u"  # 1=Monday, 7=Sunday
}

is_weekly_backup_day() {
    # Weekly backups on Sunday (7)
    [[ "$(get_day_of_week)" == "7" ]]
}

# =============================================================================
# PostgreSQL Backup
# =============================================================================

backup_postgres() {
    local timestamp
    timestamp=$(get_timestamp)
    local backup_dir="${BACKUP_ROOT}/postgres/daily"
    local backup_file="${backup_dir}/postgres_${timestamp}.sql.gz"
    
    ensure_dir "$backup_dir"
    
    log_info "Starting PostgreSQL backup..."
    
    # Check connection
    if ! PGPASSWORD="${POSTGRES_PASSWORD:-}" pg_isready -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" &>/dev/null; then
        log_error "Cannot connect to PostgreSQL at ${POSTGRES_HOST}:${POSTGRES_PORT}"
        return 1
    fi
    
    # Full dump with compression
    if PGPASSWORD="${POSTGRES_PASSWORD:-}" pg_dump \
        -h "$POSTGRES_HOST" \
        -p "$POSTGRES_PORT" \
        -U "$POSTGRES_USER" \
        -d "$POSTGRES_DB" \
        --format=custom \
        --compress=9 \
        --file="${backup_file%.gz}" 2>/dev/null; then
        
        # Additional gzip compression for custom format
        gzip -f "${backup_file%.gz}" 2>/dev/null || mv "${backup_file%.gz}" "$backup_file"
        
        local size
        size=$(du -h "$backup_file" | cut -f1)
        log_success "PostgreSQL backup completed: $backup_file ($size)"
        
        # Create weekly copy if Sunday
        if is_weekly_backup_day; then
            local weekly_dir="${BACKUP_ROOT}/postgres/weekly"
            ensure_dir "$weekly_dir"
            cp "$backup_file" "${weekly_dir}/postgres_${timestamp}_weekly.sql.gz"
            log_info "Created weekly backup copy"
        fi
        
        # Record backup metadata
        record_backup_metadata "postgres" "$backup_file" "$size"
        
        return 0
    else
        log_error "PostgreSQL backup failed"
        return 1
    fi
}

# =============================================================================
# Qdrant Backup (Vector Database Snapshots)
# =============================================================================

backup_qdrant() {
    local timestamp
    timestamp=$(get_timestamp)
    local backup_dir="${BACKUP_ROOT}/qdrant/daily"
    
    ensure_dir "$backup_dir"
    
    log_info "Starting Qdrant backup..."
    
    # Check connection
    if ! curl -sf "http://${QDRANT_HOST}:${QDRANT_PORT}/healthz" &>/dev/null; then
        log_error "Cannot connect to Qdrant at ${QDRANT_HOST}:${QDRANT_PORT}"
        return 1
    fi
    
    # Get list of collections
    local collections
    collections=$(curl -sf "http://${QDRANT_HOST}:${QDRANT_PORT}/collections" | jq -r '.result.collections[].name' 2>/dev/null || echo "")
    
    if [[ -z "$collections" ]]; then
        log_warn "No collections found in Qdrant"
        return 0
    fi
    
    local success=0
    local failed=0
    
    for collection in $collections; do
        log_info "Creating snapshot for collection: $collection"
        
        # Create snapshot via Qdrant API
        local snapshot_response
        snapshot_response=$(curl -sf -X POST "http://${QDRANT_HOST}:${QDRANT_PORT}/collections/${collection}/snapshots" 2>/dev/null || echo "")
        
        if [[ -n "$snapshot_response" ]]; then
            local snapshot_name
            snapshot_name=$(echo "$snapshot_response" | jq -r '.result.name' 2>/dev/null || echo "")
            
            if [[ -n "$snapshot_name" && "$snapshot_name" != "null" ]]; then
                # Download snapshot
                local snapshot_file="${backup_dir}/${collection}_${timestamp}.snapshot"
                if curl -sf "http://${QDRANT_HOST}:${QDRANT_PORT}/collections/${collection}/snapshots/${snapshot_name}" -o "$snapshot_file"; then
                    local size
                    size=$(du -h "$snapshot_file" | cut -f1)
                    log_success "Snapshot created: $snapshot_file ($size)"
                    ((success++))
                    
                    # Create weekly copy if Sunday
                    if is_weekly_backup_day; then
                        local weekly_dir="${BACKUP_ROOT}/qdrant/weekly"
                        ensure_dir "$weekly_dir"
                        cp "$snapshot_file" "${weekly_dir}/${collection}_${timestamp}_weekly.snapshot"
                    fi
                else
                    log_error "Failed to download snapshot for $collection"
                    ((failed++))
                fi
            else
                log_error "Failed to create snapshot for $collection"
                ((failed++))
            fi
        else
            log_error "Snapshot API call failed for $collection"
            ((failed++))
        fi
    done
    
    log_info "Qdrant backup completed: $success successful, $failed failed"
    record_backup_metadata "qdrant" "$backup_dir" "${success} collections"
    
    [[ $failed -eq 0 ]]
}

# =============================================================================
# OpenWebUI Configuration Backup
# =============================================================================

backup_openwebui() {
    local timestamp
    timestamp=$(get_timestamp)
    local backup_dir="${BACKUP_ROOT}/openwebui/daily"
    local backup_file="${backup_dir}/openwebui_${timestamp}.tar.gz"
    
    ensure_dir "$backup_dir"
    
    log_info "Starting OpenWebUI configuration backup..."
    
    if [[ ! -d "$OPENWEBUI_DATA" ]]; then
        log_warn "OpenWebUI data directory not found: $OPENWEBUI_DATA"
        return 1
    fi
    
    # Create tarball of config data (excluding large cache files)
    if tar -czf "$backup_file" \
        --exclude='*.cache' \
        --exclude='__pycache__' \
        --exclude='*.pyc' \
        --exclude='uploads/*' \
        -C "$(dirname "$OPENWEBUI_DATA")" \
        "$(basename "$OPENWEBUI_DATA")" 2>/dev/null; then
        
        local size
        size=$(du -h "$backup_file" | cut -f1)
        log_success "OpenWebUI backup completed: $backup_file ($size)"
        
        # Create weekly copy if Sunday
        if is_weekly_backup_day; then
            local weekly_dir="${BACKUP_ROOT}/openwebui/weekly"
            ensure_dir "$weekly_dir"
            cp "$backup_file" "${weekly_dir}/openwebui_${timestamp}_weekly.tar.gz"
            log_info "Created weekly backup copy"
        fi
        
        record_backup_metadata "openwebui" "$backup_file" "$size"
        return 0
    else
        log_error "OpenWebUI backup failed"
        return 1
    fi
}

# =============================================================================
# Configuration Files Backup
# =============================================================================

backup_configs() {
    local timestamp
    timestamp=$(get_timestamp)
    local backup_dir="${BACKUP_ROOT}/configs/daily"
    local backup_file="${backup_dir}/configs_${timestamp}.tar.gz"
    
    ensure_dir "$backup_dir"
    
    log_info "Starting configuration files backup..."
    
    # Backup project config files
    local config_files=(
        "${PROJECT_ROOT}/config"
        "${PROJECT_ROOT}/helm/server/values.yaml"
        "${PROJECT_ROOT}/helm/gpu-worker/values.yaml"
        "${PROJECT_ROOT}/helmfile/environments"
        "${PROJECT_ROOT}/server/monitoring"
    )
    
    local temp_dir
    temp_dir=$(mktemp -d)
    
    for path in "${config_files[@]}"; do
        if [[ -e "$path" ]]; then
            local rel_path="${path#${PROJECT_ROOT}/}"
            local dest_dir="${temp_dir}/$(dirname "$rel_path")"
            mkdir -p "$dest_dir"
            cp -r "$path" "$dest_dir/"
        fi
    done
    
    if tar -czf "$backup_file" -C "$temp_dir" . 2>/dev/null; then
        local size
        size=$(du -h "$backup_file" | cut -f1)
        log_success "Config backup completed: $backup_file ($size)"
        
        # Create weekly copy if Sunday
        if is_weekly_backup_day; then
            local weekly_dir="${BACKUP_ROOT}/configs/weekly"
            ensure_dir "$weekly_dir"
            cp "$backup_file" "${weekly_dir}/configs_${timestamp}_weekly.tar.gz"
        fi
        
        record_backup_metadata "configs" "$backup_file" "$size"
    else
        log_error "Config backup failed"
    fi
    
    rm -rf "$temp_dir"
}

# =============================================================================
# Retention Management
# =============================================================================

cleanup_old_backups() {
    log_info "Cleaning up old backups..."
    
    local components=("postgres" "qdrant" "openwebui" "configs")
    
    for component in "${components[@]}"; do
        # Daily cleanup
        local daily_dir="${BACKUP_ROOT}/${component}/daily"
        if [[ -d "$daily_dir" ]]; then
            find "$daily_dir" -type f -mtime +"$LOCAL_RETENTION_DAILY" -delete 2>/dev/null || true
            log_info "Cleaned daily backups for $component (keeping last $LOCAL_RETENTION_DAILY days)"
        fi
        
        # Weekly cleanup
        local weekly_dir="${BACKUP_ROOT}/${component}/weekly"
        if [[ -d "$weekly_dir" ]]; then
            # Keep only last N weekly backups
            local weekly_count
            weekly_count=$(find "$weekly_dir" -type f 2>/dev/null | wc -l)
            if [[ $weekly_count -gt $LOCAL_RETENTION_WEEKLY ]]; then
                find "$weekly_dir" -type f -printf '%T@ %p\n' 2>/dev/null | \
                    sort -n | head -n -"$LOCAL_RETENTION_WEEKLY" | \
                    awk '{print $2}' | xargs -r rm -f
                log_info "Cleaned weekly backups for $component (keeping last $LOCAL_RETENTION_WEEKLY)"
            fi
        fi
    done
    
    log_success "Backup cleanup completed"
}

# =============================================================================
# Remote Archival
# =============================================================================

archive_to_remote() {
    if [[ "$REMOTE_ENABLED" != "true" ]]; then
        log_info "Remote archival is disabled"
        return 0
    fi
    
    if [[ -z "$REMOTE_BUCKET" ]]; then
        log_error "REMOTE_BUCKET is required for remote archival"
        return 1
    fi
    
    log_info "Archiving backups to remote storage ($REMOTE_TYPE)..."
    
    local weekly_dirs=(
        "${BACKUP_ROOT}/postgres/weekly"
        "${BACKUP_ROOT}/qdrant/weekly"
        "${BACKUP_ROOT}/openwebui/weekly"
        "${BACKUP_ROOT}/configs/weekly"
    )
    
    for dir in "${weekly_dirs[@]}"; do
        if [[ ! -d "$dir" ]]; then
            continue
        fi
        
        local component
        component=$(basename "$(dirname "$dir")")
        local remote_path
        
        case "$REMOTE_TYPE" in
            s3)
                remote_path="s3://${REMOTE_BUCKET}/${REMOTE_PREFIX}/${component}/"
                if command -v aws &>/dev/null; then
                    aws s3 sync "$dir" "$remote_path" --storage-class STANDARD_IA
                    log_success "Archived $component to S3"
                else
                    log_error "AWS CLI not found, skipping S3 archival"
                fi
                ;;
            gcs)
                remote_path="gs://${REMOTE_BUCKET}/${REMOTE_PREFIX}/${component}/"
                if command -v gsutil &>/dev/null; then
                    gsutil -m rsync -r "$dir" "$remote_path"
                    log_success "Archived $component to GCS"
                else
                    log_error "gsutil not found, skipping GCS archival"
                fi
                ;;
            *)
                log_error "Unknown remote type: $REMOTE_TYPE"
                ;;
        esac
    done
}

# =============================================================================
# Backup Metadata & Metrics
# =============================================================================

record_backup_metadata() {
    local component="$1"
    local path="$2"
    local size="$3"
    local timestamp
    timestamp=$(date -Iseconds)
    
    local metadata_file="${BACKUP_ROOT}/metadata.json"
    
    # Create or update metadata file
    local entry
    entry=$(jq -n \
        --arg component "$component" \
        --arg path "$path" \
        --arg size "$size" \
        --arg timestamp "$timestamp" \
        --arg status "success" \
        '{component: $component, path: $path, size: $size, timestamp: $timestamp, status: $status}')
    
    if [[ -f "$metadata_file" ]]; then
        local updated
        updated=$(jq --argjson entry "$entry" '.backups += [$entry] | .last_backup = $entry.timestamp' "$metadata_file")
        echo "$updated" > "$metadata_file"
    else
        echo "{\"backups\": [$entry], \"last_backup\": \"$timestamp\"}" | jq . > "$metadata_file"
    fi
    
    # Export Prometheus metrics (if textfile collector directory exists)
    local metrics_dir="/var/lib/node_exporter/textfile_collector"
    if [[ -d "$metrics_dir" ]]; then
        cat > "${metrics_dir}/backup_${component}.prom" << EOF
# HELP backup_last_success_timestamp_seconds Last successful backup timestamp
# TYPE backup_last_success_timestamp_seconds gauge
backup_last_success_timestamp_seconds{component="${component}"} $(date +%s)
# HELP backup_size_bytes Size of last backup in bytes
# TYPE backup_size_bytes gauge
backup_size_bytes{component="${component}"} $(stat -c%s "$path" 2>/dev/null || echo 0)
EOF
    fi
}

# =============================================================================
# Verification
# =============================================================================

verify_backup() {
    local component="$1"
    local backup_file="$2"
    
    log_info "Verifying backup: $backup_file"
    
    case "$component" in
        postgres)
            # Verify pg_dump custom format
            if pg_restore --list "$backup_file" &>/dev/null; then
                log_success "PostgreSQL backup verified"
                return 0
            else
                log_error "PostgreSQL backup verification failed"
                return 1
            fi
            ;;
        qdrant)
            # Verify snapshot file integrity
            if [[ -f "$backup_file" && -s "$backup_file" ]]; then
                log_success "Qdrant snapshot verified (file exists and non-empty)"
                return 0
            else
                log_error "Qdrant snapshot verification failed"
                return 1
            fi
            ;;
        *)
            # Verify tarball
            if tar -tzf "$backup_file" &>/dev/null; then
                log_success "Backup archive verified"
                return 0
            else
                log_error "Backup archive verification failed"
                return 1
            fi
            ;;
    esac
}

# =============================================================================
# Commands
# =============================================================================

cmd_all() {
    log_info "Running full backup of all components..."
    
    local failed=0
    
    backup_postgres || ((failed++))
    backup_qdrant || ((failed++))
    backup_openwebui || ((failed++))
    backup_configs || ((failed++))
    
    cleanup_old_backups
    
    if [[ "$1" == "--archive" ]] || [[ "${REMOTE_ENABLED:-false}" == "true" ]]; then
        archive_to_remote
    fi
    
    if [[ $failed -eq 0 ]]; then
        log_success "All backups completed successfully"
    else
        log_error "$failed backup(s) failed"
        return 1
    fi
}

cmd_postgres() {
    backup_postgres
    cleanup_old_backups
}

cmd_qdrant() {
    backup_qdrant
    cleanup_old_backups
}

cmd_openwebui() {
    backup_openwebui
    cleanup_old_backups
}

cmd_configs() {
    backup_configs
    cleanup_old_backups
}

cmd_cleanup() {
    cleanup_old_backups
}

cmd_archive() {
    REMOTE_ENABLED=true archive_to_remote
}

cmd_status() {
    local metadata_file="${BACKUP_ROOT}/metadata.json"
    
    echo -e "\n${BLUE}=== Backup Status ===${NC}\n"
    
    if [[ -f "$metadata_file" ]]; then
        echo "Last backup: $(jq -r '.last_backup' "$metadata_file")"
        echo ""
        echo "Recent backups:"
        jq -r '.backups[-5:] | .[] | "  \(.timestamp) | \(.component) | \(.size) | \(.status)"' "$metadata_file"
    else
        echo "No backup metadata found"
    fi
    
    echo ""
    echo "Local storage usage:"
    for component in postgres qdrant openwebui configs; do
        local daily_size weekly_size
        daily_size=$(du -sh "${BACKUP_ROOT}/${component}/daily" 2>/dev/null | cut -f1 || echo "0")
        weekly_size=$(du -sh "${BACKUP_ROOT}/${component}/weekly" 2>/dev/null | cut -f1 || echo "0")
        printf "  %-12s daily: %8s  weekly: %8s\n" "$component" "$daily_size" "$weekly_size"
    done
    
    echo ""
    echo "Retention policy:"
    echo "  Daily: ${LOCAL_RETENTION_DAILY} days"
    echo "  Weekly: ${LOCAL_RETENTION_WEEKLY} weeks"
    echo "  Remote archival: ${REMOTE_ENABLED}"
}

cmd_help() {
    cat << EOF
Usage: $(basename "$0") <command> [options]

Component Backup Commands:
  all [--archive]   Backup all components (optionally archive to remote)
  postgres          Backup PostgreSQL database
  qdrant            Backup Qdrant vector database (collection snapshots)
  openwebui         Backup OpenWebUI configuration and data
  configs           Backup project configuration files

Management Commands:
  cleanup           Clean up old backups based on retention policy
  archive           Archive weekly backups to remote storage (S3/GCS)
  status            Show backup status and storage usage
  help              Show this help message

Environment Variables:
  BACKUP_ROOT              Base directory for backups (default: /data/backups)
  LOCAL_RETENTION_DAILY    Days to keep daily backups (default: 7)
  LOCAL_RETENTION_WEEKLY   Weeks to keep weekly backups (default: 4)
  REMOTE_ENABLED           Enable remote archival (default: false)
  REMOTE_TYPE              Remote storage type: s3, gcs (default: s3)
  REMOTE_BUCKET            Remote storage bucket name
  REMOTE_PREFIX            Remote storage prefix (default: self-hosted-ai/backups)
  
  POSTGRES_HOST/PORT/USER/DB/PASSWORD  PostgreSQL connection settings
  QDRANT_HOST/PORT                     Qdrant connection settings
  OPENWEBUI_DATA                       OpenWebUI data directory

Examples:
  $(basename "$0") all                    # Backup everything
  $(basename "$0") all --archive          # Backup and archive to remote
  $(basename "$0") postgres               # Backup only PostgreSQL
  $(basename "$0") status                 # Show backup status

EOF
}

# =============================================================================
# Main Entry Point
# =============================================================================

main() {
    local command="${1:-help}"
    shift || true
    
    case "$command" in
        all)        cmd_all "$@" ;;
        postgres)   cmd_postgres ;;
        qdrant)     cmd_qdrant ;;
        openwebui)  cmd_openwebui ;;
        configs)    cmd_configs ;;
        cleanup)    cmd_cleanup ;;
        archive)    cmd_archive ;;
        status)     cmd_status ;;
        help|--help|-h) cmd_help ;;
        *)
            log_error "Unknown command: $command"
            cmd_help
            exit 1
            ;;
    esac
}

main "$@"
