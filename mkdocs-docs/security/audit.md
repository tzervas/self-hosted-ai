---
title: Security Audit
description: Security audit findings, TLS validation, and compliance
---

# Security Audit

## TLS Validation Audit

### Summary

A security audit identified CWE-295 (Improper Certificate Validation) vulnerabilities where services had `insecureSkipVerify: true` configured, creating potential MITM attack vectors.

### Status

| Service | Status | Fix |
|---------|--------|-----|
| ArgoCD | Fixed | Replaced `insecureSkipVerify` with `rootCA` |
| oauth2-proxy | Remediation pending | Configure CA trust |
| Grafana | Remediation pending | Configure CA trust |

### Automated Fix

```bash
# Scan and fix TLS validation issues
uv run scripts/fix-tls-validation.py fix
```

### Compliance Implications

| Framework | Requirement | Status |
|-----------|-------------|--------|
| CIS Kubernetes | TLS validation required | Partial |
| NIST 800-53 | SC-8 (Transmission Confidentiality) | In progress |
| PCI-DSS | 4.1 (Strong cryptography) | In progress |

## Security Scanning

```bash
# Trivy configuration scan
task security:trivy

# Secret detection
task security:secrets
```

## Security Checklist

- [x] SealedSecrets for all credentials
- [x] Internal CA for TLS
- [x] Non-root containers
- [x] Pod Security Standards (Baseline)
- [x] NetworkPolicy default-deny
- [x] Linkerd mTLS
- [ ] Complete TLS validation fix (2 services remaining)
- [ ] External vulnerability scanning
- [ ] Automated security scanning in CI
