---
title: Backup & Recovery
description: Backup procedures and disaster recovery
---

# Backup & Recovery

## Backup Commands

```bash
# Full backup (PostgreSQL, Qdrant, OpenWebUI)
uv run scripts/backup.py create --all

# List backups
uv run scripts/backup.py list

# Restore from backup
uv run scripts/backup.py restore 20260115_120000

# Cleanup old backups (keep last 5)
uv run scripts/backup.py cleanup --keep 5
```

## What Gets Backed Up

| Component | Data | Method |
|-----------|------|--------|
| PostgreSQL | LiteLLM config, n8n workflows | `pg_dump` |
| Open WebUI | Chat history, settings | API export |
| Longhorn | Persistent volumes | Longhorn snapshots |
| Git | All configuration | Git repository |
| SealedSecrets | Encryption key | Manual backup |

## Backup Schedule

Backups should be configured to run daily. Critical data:

1. **PostgreSQL** - Daily `pg_dump` to NFS share
2. **SealedSecrets key** - Manual backup to secure location
3. **Longhorn volumes** - Scheduled snapshots via Longhorn UI

!!! warning "SealedSecrets Key"
    The SealedSecrets encryption key is critical. If lost, all encrypted secrets become unrecoverable. Back up the key from `kube-system` namespace to a secure, offline location.

## Disaster Recovery

For full cluster recovery procedures, see [Troubleshooting - Emergency Procedures](troubleshooting.md#emergency-procedures).
