"""Configuration validation tests.

Validates Helm charts, YAML configurations, and Kubernetes manifests
without requiring cluster access for static checks.
"""

import subprocess
from pathlib import Path

import pytest
import yaml


pytestmark = [pytest.mark.platform]

PROJECT_ROOT = Path(__file__).parent.parent.parent


class TestHelmCharts:
    """Validate Helm chart structure and syntax."""

    @pytest.fixture(scope="class")
    def helm_charts(self):
        """Discover all Helm charts in the helm/ directory."""
        helm_dir = PROJECT_ROOT / "helm"
        charts = []
        for chart_dir in sorted(helm_dir.iterdir()):
            if chart_dir.is_dir() and (chart_dir / "Chart.yaml").exists():
                charts.append(chart_dir)
        return charts

    def test_helm_charts_discovered(self, helm_charts):
        """At least 10 Helm charts should exist."""
        assert len(helm_charts) >= 10, (
            f"Expected at least 10 Helm charts, found {len(helm_charts)}"
        )

    def test_charts_have_values(self, helm_charts):
        """Each Helm chart should have a values.yaml file."""
        missing = []
        for chart in helm_charts:
            if not (chart / "values.yaml").exists():
                missing.append(chart.name)
        assert not missing, (
            f"Charts missing values.yaml: {missing}"
        )

    def test_helm_lint_passes(self, helm_charts):
        """All Helm charts should pass helm lint."""
        failures = []
        for chart in helm_charts:
            result = subprocess.run(
                ["helm", "lint", str(chart)],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode != 0:
                failures.append(f"{chart.name}: {result.stderr.strip()}")

        assert not failures, (
            f"Helm lint failures:\n" +
            "\n".join(f"  - {f}" for f in failures)
        )

    def test_chart_yaml_valid(self, helm_charts):
        """Chart.yaml files should be valid YAML with required fields."""
        issues = []
        for chart in helm_charts:
            chart_yaml = chart / "Chart.yaml"
            try:
                with open(chart_yaml) as f:
                    data = yaml.safe_load(f)
                if not data.get("apiVersion"):
                    issues.append(f"{chart.name}: missing apiVersion")
                if not data.get("name"):
                    issues.append(f"{chart.name}: missing name")
            except yaml.YAMLError as e:
                issues.append(f"{chart.name}: invalid YAML: {e}")

        assert not issues, (
            f"Chart.yaml issues:\n" +
            "\n".join(f"  - {i}" for i in issues)
        )


class TestArgocdApplications:
    """Validate ArgoCD application manifest syntax."""

    @pytest.fixture(scope="class")
    def app_manifests(self):
        """Load all ArgoCD application YAML files."""
        apps_dir = PROJECT_ROOT / "argocd" / "applications"
        manifests = []
        for yaml_file in sorted(apps_dir.glob("*.yaml")):
            try:
                with open(yaml_file) as f:
                    data = yaml.safe_load(f)
                manifests.append((yaml_file.name, data))
            except yaml.YAMLError as e:
                manifests.append((yaml_file.name, {"_error": str(e)}))
        return manifests

    def test_app_manifests_valid_yaml(self, app_manifests):
        """All ArgoCD application files should be valid YAML."""
        errors = [
            name for name, data in app_manifests
            if "_error" in (data or {})
        ]
        assert not errors, f"Invalid YAML files: {errors}"

    def test_apps_have_sync_wave(self, app_manifests):
        """ArgoCD applications should have sync-wave annotations."""
        missing = []
        for name, data in app_manifests:
            if data is None or "_error" in data:
                continue
            annotations = data.get("metadata", {}).get("annotations", {})
            if "argocd.argoproj.io/sync-wave" not in annotations:
                missing.append(name)

        # Sync waves are recommended but not always required
        if missing:
            pytest.xfail(
                f"Apps without sync-wave annotation (may be intentional): {missing}"
            )

    def test_apps_reference_valid_paths(self, app_manifests):
        """ArgoCD app sources should reference paths that exist."""
        bad_paths = []
        for name, data in app_manifests:
            if data is None or "_error" in data:
                continue
            spec = data.get("spec", {})
            source = spec.get("source", {})
            path = source.get("path", "")
            if path and path.startswith("helm/"):
                full_path = PROJECT_ROOT / path
                if not full_path.exists():
                    bad_paths.append(f"{name}: {path}")

        assert not bad_paths, (
            f"ArgoCD apps reference non-existent paths:\n" +
            "\n".join(f"  - {p}" for p in bad_paths)
        )


class TestModelConfiguration:
    """Validate AI model configuration files."""

    def test_models_manifest_valid(self):
        """models-manifest.yml should be valid and complete."""
        manifest_path = PROJECT_ROOT / "config" / "models-manifest.yml"
        assert manifest_path.exists(), "models-manifest.yml not found"

        with open(manifest_path) as f:
            data = yaml.safe_load(f)

        assert "gpu_worker" in data, "Missing gpu_worker section"
        assert "cpu_server" in data, "Missing cpu_server section"
        assert "models" in data["gpu_worker"], "Missing gpu_worker.models"
        assert "models" in data["cpu_server"], "Missing cpu_server.models"

        # Validate model entries have required fields
        for section in ["gpu_worker", "cpu_server"]:
            for model in data[section]["models"]:
                assert "name" in model, f"Model missing name in {section}"
                assert "size" in model, f"Model {model.get('name')} missing size"
                assert "purpose" in model, f"Model {model.get('name')} missing purpose"
                assert "priority" in model, f"Model {model.get('name')} missing priority"

    def test_litellm_config_valid(self):
        """litellm-config.yml should be valid with model routing."""
        config_path = PROJECT_ROOT / "config" / "litellm-config.yml"
        assert config_path.exists(), "litellm-config.yml not found"

        with open(config_path) as f:
            data = yaml.safe_load(f)

        assert "model_list" in data, "Missing model_list"
        assert len(data["model_list"]) >= 5, (
            f"Expected at least 5 models, found {len(data['model_list'])}"
        )

        # Verify each model has required fields
        for model in data["model_list"]:
            assert "model_name" in model, f"Model missing model_name"
            assert "litellm_params" in model, (
                f"Model {model.get('model_name')} missing litellm_params"
            )
            params = model["litellm_params"]
            assert "model" in params, (
                f"Model {model.get('model_name')} missing litellm_params.model"
            )
            assert "api_base" in params, (
                f"Model {model.get('model_name')} missing litellm_params.api_base"
            )

    def test_litellm_config_has_router_settings(self):
        """LiteLLM should have router settings for fallback."""
        config_path = PROJECT_ROOT / "config" / "litellm-config.yml"
        with open(config_path) as f:
            data = yaml.safe_load(f)

        assert "router_settings" in data, "Missing router_settings"
        router = data["router_settings"]
        assert router.get("enable_fallbacks") is True, "Fallbacks should be enabled"
        assert "fallbacks" in router, "Missing fallback chains"


class TestSealedSecrets:
    """Validate sealed secret manifests."""

    def test_sealed_secrets_exist(self):
        """Sealed secret files should exist."""
        secrets_dir = PROJECT_ROOT / "argocd" / "sealed-secrets"
        assert secrets_dir.exists(), "argocd/sealed-secrets/ directory not found"
        secrets = list(secrets_dir.glob("*.yaml"))
        assert len(secrets) >= 5, (
            f"Expected at least 5 sealed secrets, found {len(secrets)}"
        )

    def test_sealed_secrets_valid_yaml(self):
        """All sealed secret files should be valid YAML."""
        secrets_dir = PROJECT_ROOT / "argocd" / "sealed-secrets"
        errors = []
        for secret_file in secrets_dir.glob("*.yaml"):
            try:
                with open(secret_file) as f:
                    data = yaml.safe_load(f)
                if data is None:
                    errors.append(f"{secret_file.name}: empty file")
            except yaml.YAMLError as e:
                errors.append(f"{secret_file.name}: {e}")

        assert not errors, (
            f"Invalid sealed secret files:\n" +
            "\n".join(f"  - {e}" for e in errors)
        )
