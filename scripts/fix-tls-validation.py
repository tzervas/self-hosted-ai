#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["pyyaml"]
# ///
"""
Fix TLS Certificate Validation in Services

Automatically updates service configurations to use proper CA trust instead of
insecureSkipVerify. Addresses CWE-295 vulnerability in oauth2-proxy and Grafana.

Usage:
    uv run scripts/fix-tls-validation.py check        # Check current status
    uv run scripts/fix-tls-validation.py fix          # Apply fixes
    uv run scripts/fix-tls-validation.py verify       # Verify fixes work
"""

import sys
import re
from pathlib import Path
from typing import Dict, List, Tuple
import subprocess
import yaml

PROJECT_ROOT = Path(__file__).parent.parent
HELM_DIR = PROJECT_ROOT / "helm"
ARGOCD_HELM_DIR = PROJECT_ROOT / "argocd" / "helm"


class Colors:
    """ANSI color codes for terminal output"""

    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    BLUE = "\033[0;34m"
    CYAN = "\033[0;36m"
    NC = "\033[0m"  # No Color


def print_header(title: str):
    """Print section header"""
    print(f"\n{Colors.BLUE}{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}{Colors.NC}\n")


def print_status(message: str, status: str):
    """Print status message with color"""
    color = Colors.GREEN if status == "OK" else Colors.YELLOW if status == "WARN" else Colors.RED
    print(f"{color}[{status}]{Colors.NC} {message}")


def check_oauth2_proxy() -> Tuple[bool, str]:
    """Check oauth2-proxy TLS configuration"""
    values_file = HELM_DIR / "oauth2-proxy" / "values.yaml"

    if not values_file.exists():
        return False, f"Values file not found: {values_file}"

    content = values_file.read_text()

    # Check for insecure skip verify
    if "sslInsecureSkipVerify: true" in content:
        return False, "Using sslInsecureSkipVerify: true (INSECURE)"

    # Check for proper CA configuration
    if "SSL_CERT_FILE" in content or "extraVolumeMounts" in content:
        return True, "Proper CA trust configured"

    return False, "No explicit TLS configuration found"


def check_grafana() -> Tuple[bool, str]:
    """Check Grafana TLS configuration"""
    values_file = ARGOCD_HELM_DIR / "prometheus" / "values.yaml"

    if not values_file.exists():
        return False, f"Values file not found: {values_file}"

    content = values_file.read_text()

    # Check for insecure skip verify
    if "tls_skip_verify_insecure: true" in content:
        return False, "Using tls_skip_verify_insecure: true (INSECURE)"

    # Check for proper CA configuration
    if "tls_client_ca:" in content:
        return True, "Proper CA trust configured"

    return False, "No explicit TLS configuration found"


def check_argocd() -> Tuple[bool, str]:
    """Check ArgoCD TLS configuration"""
    configmap_file = HELM_DIR / "argocd-config" / "templates" / "configmap.yaml"

    if not configmap_file.exists():
        return False, f"ConfigMap file not found: {configmap_file}"

    content = configmap_file.read_text()

    # Check for insecure skip verify
    if "insecureSkipVerify: true" in content:
        return False, "Using insecureSkipVerify: true (INSECURE)"

    # Check for rootCA
    if "rootCA:" in content and "argocd-config.rootCA" in content:
        return True, "Proper rootCA configured"

    return False, "No explicit TLS configuration found"


def fix_oauth2_proxy() -> bool:
    """Fix oauth2-proxy TLS validation"""
    values_file = HELM_DIR / "oauth2-proxy" / "values.yaml"

    print_header("Fixing oauth2-proxy TLS Validation")

    try:
        with open(values_file, "r") as f:
            data = yaml.safe_load(f)

        # Disable insecure skip verify
        if "config" in data and "sslInsecureSkipVerify" in data["config"]:
            data["config"]["sslInsecureSkipVerify"] = False
            print_status("Disabled sslInsecureSkipVerify", "OK")

        # Add CA certificate volume mount
        if "extraVolumes" not in data:
            data["extraVolumes"] = []

        ca_volume = {
            "name": "ca-bundle",
            "secret": {"secretName": "vectorweight-root-ca", "defaultMode": 420},
        }

        # Check if volume already exists
        volume_exists = any(v.get("name") == "ca-bundle" for v in data["extraVolumes"])
        if not volume_exists:
            data["extraVolumes"].append(ca_volume)
            print_status("Added CA certificate volume", "OK")

        # Add volume mount
        if "extraVolumeMounts" not in data:
            data["extraVolumeMounts"] = []

        ca_mount = {
            "name": "ca-bundle",
            "mountPath": "/etc/ssl/certs/vectorweight-ca.crt",
            "subPath": "tls.crt",
            "readOnly": True,
        }

        mount_exists = any(m.get("name") == "ca-bundle" for m in data["extraVolumeMounts"])
        if not mount_exists:
            data["extraVolumeMounts"].append(ca_mount)
            print_status("Added CA certificate mount", "OK")

        # Add environment variable
        if "extraEnv" not in data:
            data["extraEnv"] = []

        env_var = {"name": "SSL_CERT_FILE", "value": "/etc/ssl/certs/vectorweight-ca.crt"}

        env_exists = any(e.get("name") == "SSL_CERT_FILE" for e in data["extraEnv"])
        if not env_exists:
            data["extraEnv"].append(env_var)
            print_status("Added SSL_CERT_FILE environment variable", "OK")

        # Write back to file
        with open(values_file, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

        print_status(f"Updated {values_file}", "OK")
        return True

    except Exception as e:
        print_status(f"Error fixing oauth2-proxy: {e}", "FAIL")
        return False


def fix_grafana() -> bool:
    """Fix Grafana TLS validation"""
    values_file = ARGOCD_HELM_DIR / "prometheus" / "values.yaml"

    print_header("Fixing Grafana TLS Validation")

    try:
        with open(values_file, "r") as f:
            content = f.read()

        # Replace tls_skip_verify_insecure
        content = re.sub(
            r"tls_skip_verify_insecure:\s*true",
            "tls_skip_verify_insecure: false",
            content,
        )

        # Check if extraSecretMounts exists
        if "extraSecretMounts:" not in content:
            # Find grafana.ini section and add mounts after it
            grafana_section = re.search(
                r"(grafana:\s*\n(?:\s+[^\n]+\n)*)", content, re.MULTILINE
            )

            if grafana_section:
                insert_pos = grafana_section.end()

                mount_config = """  # Mount CA certificate for TLS validation
  extraSecretMounts:
    - name: ca-cert
      secretName: vectorweight-root-ca
      defaultMode: 0444
      mountPath: /etc/grafana/ca
      readOnly: true
"""
                content = content[:insert_pos] + mount_config + content[insert_pos:]
                print_status("Added CA certificate mount configuration", "OK")

        # Add tls_client_ca setting if not present
        if "tls_client_ca:" not in content:
            # Find auth.generic_oauth section
            oauth_section = re.search(
                r"(auth\.generic_oauth:\s*\n(?:\s+[^\n]+\n)*)", content, re.MULTILINE
            )

            if oauth_section:
                lines = oauth_section.group(0).split("\n")
                # Add tls_client_ca after tls_skip_verify_insecure
                for i, line in enumerate(lines):
                    if "tls_skip_verify_insecure:" in line:
                        indent = len(line) - len(line.lstrip())
                        lines.insert(
                            i + 1,
                            " " * indent + "tls_client_ca: /etc/grafana/ca/tls.crt",
                        )
                        break

                new_section = "\n".join(lines)
                content = content.replace(oauth_section.group(0), new_section)
                print_status("Added tls_client_ca configuration", "OK")

        # Write back
        with open(values_file, "w") as f:
            f.write(content)

        print_status(f"Updated {values_file}", "OK")
        return True

    except Exception as e:
        print_status(f"Error fixing Grafana: {e}", "FAIL")
        return False


def verify_kubernetes_secret() -> bool:
    """Verify the vectorweight-root-ca secret exists"""
    print_header("Verifying Kubernetes Secret")

    try:
        result = subprocess.run(
            [
                "kubectl",
                "get",
                "secret",
                "vectorweight-root-ca",
                "-n",
                "cert-manager",
                "-o",
                "json",
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        print_status("vectorweight-root-ca secret exists in cert-manager namespace", "OK")

        # Parse and show certificate info
        import json

        secret_data = json.loads(result.stdout)
        cert_b64 = secret_data["data"]["tls.crt"]

        # Decode and check certificate
        import base64

        cert_pem = base64.b64decode(cert_b64)

        # Write to temp file and check with openssl
        import tempfile

        with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=".crt") as f:
            f.write(cert_pem)
            temp_cert = f.name

        cert_info = subprocess.run(
            ["openssl", "x509", "-in", temp_cert, "-noout", "-subject", "-enddate"],
            capture_output=True,
            text=True,
            check=True,
        )

        print(f"{Colors.CYAN}{cert_info.stdout}{Colors.NC}")
        Path(temp_cert).unlink()

        return True

    except subprocess.CalledProcessError as e:
        print_status(f"Secret not found: {e.stderr}", "FAIL")
        return False
    except Exception as e:
        print_status(f"Error verifying secret: {e}", "FAIL")
        return False


def check_status():
    """Check current TLS validation status"""
    print_header("TLS Validation Status Check")

    services = {
        "ArgoCD": check_argocd(),
        "oauth2-proxy": check_oauth2_proxy(),
        "Grafana": check_grafana(),
    }

    for service, (ok, message) in services.items():
        status = "OK" if ok else "FAIL"
        print_status(f"{service}: {message}", status)

    # Summary
    print("\n" + "=" * 60)
    total = len(services)
    passing = sum(1 for ok, _ in services.values() if ok)
    failing = total - passing

    if failing == 0:
        print_status(f"All {total} services have proper TLS validation", "OK")
    else:
        print_status(
            f"{passing}/{total} services secure, {failing} need fixing", "WARN"
        )


def apply_fixes():
    """Apply all TLS validation fixes"""
    print_header("Applying TLS Validation Fixes")

    # Check prerequisites
    if not verify_kubernetes_secret():
        print_status("Cannot proceed without vectorweight-root-ca secret", "FAIL")
        return False

    # Apply fixes
    results = {
        "oauth2-proxy": fix_oauth2_proxy(),
        "Grafana": fix_grafana(),
    }

    # Summary
    print_header("Fix Summary")
    success = sum(1 for result in results.values() if result)
    total = len(results)

    if success == total:
        print_status(f"All {total} fixes applied successfully", "OK")
        print(f"\n{Colors.CYAN}Next steps:{Colors.NC}")
        print("  1. Review the changes in git diff")
        print("  2. Commit to dev branch")
        print("  3. Sync ArgoCD applications:")
        print("     argocd app sync oauth2-proxy")
        print("     argocd app sync prometheus")
        print("  4. Restart pods to load new configuration")
        print("  5. Test SSO logins")
        return True
    else:
        print_status(f"Only {success}/{total} fixes succeeded", "WARN")
        return False


def verify_deployment():
    """Verify fixes are working in deployed services"""
    print_header("Verifying Deployed Services")

    try:
        # Check oauth2-proxy pod logs for certificate errors
        print("Checking oauth2-proxy logs...")
        result = subprocess.run(
            [
                "kubectl",
                "logs",
                "-n",
                "automation",
                "-l",
                "app.kubernetes.io/name=oauth2-proxy",
                "--tail=50",
            ],
            capture_output=True,
            text=True,
        )

        if "certificate" in result.stdout.lower() or "tls" in result.stdout.lower():
            print_status("Found TLS-related log entries", "WARN")
            print(result.stdout[-500:])  # Last 500 chars
        else:
            print_status("No TLS errors in oauth2-proxy logs", "OK")

        # Check Grafana pod logs
        print("\nChecking Grafana logs...")
        result = subprocess.run(
            [
                "kubectl",
                "logs",
                "-n",
                "monitoring",
                "-l",
                "app.kubernetes.io/name=grafana",
                "--tail=50",
            ],
            capture_output=True,
            text=True,
        )

        if "certificate" in result.stdout.lower() or "tls" in result.stdout.lower():
            print_status("Found TLS-related log entries", "WARN")
            print(result.stdout[-500:])
        else:
            print_status("No TLS errors in Grafana logs", "OK")

        return True

    except subprocess.CalledProcessError as e:
        print_status(f"Error checking logs: {e}", "FAIL")
        return False


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} {{check|fix|verify}}")
        print("\nCommands:")
        print("  check   - Check current TLS validation status")
        print("  fix     - Apply fixes to all services")
        print("  verify  - Verify fixes are working in cluster")
        sys.exit(1)

    command = sys.argv[1]

    if command == "check":
        check_status()
    elif command == "fix":
        if apply_fixes():
            print(f"\n{Colors.GREEN}✓ Fixes applied successfully{Colors.NC}")
            sys.exit(0)
        else:
            print(f"\n{Colors.RED}✗ Some fixes failed{Colors.NC}")
            sys.exit(1)
    elif command == "verify":
        if verify_deployment():
            print(f"\n{Colors.GREEN}✓ Verification complete{Colors.NC}")
            sys.exit(0)
        else:
            print(f"\n{Colors.YELLOW}⚠ Check warnings above{Colors.NC}")
            sys.exit(1)
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
