"""
Kubernetes Async Client
=======================
Async utilities for Kubernetes operations.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any, AsyncGenerator

from kubernetes_asyncio import client, config
from kubernetes_asyncio.client import ApiClient, CoreV1Api, CustomObjectsApi
from rich.console import Console

from lib.config import Settings, get_settings

if TYPE_CHECKING:
    from kubernetes_asyncio.client import V1Namespace, V1Pod, V1Secret, V1Service

console = Console()


class KubernetesClient:
    """Async Kubernetes client wrapper with convenience methods."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._api_client: ApiClient | None = None
        self._core_v1: CoreV1Api | None = None
        self._custom_objects: CustomObjectsApi | None = None

    async def __aenter__(self) -> "KubernetesClient":
        await self.connect()
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    async def connect(self) -> None:
        """Initialize the Kubernetes client."""
        try:
            if self.settings.kubeconfig:
                await config.load_kube_config(
                    config_file=str(self.settings.kubeconfig),
                    context=self.settings.context,
                )
            else:
                await config.load_kube_config(context=self.settings.context)
        except config.ConfigException:
            # Fall back to in-cluster config
            config.load_incluster_config()

        self._api_client = ApiClient()
        self._core_v1 = CoreV1Api(self._api_client)
        self._custom_objects = CustomObjectsApi(self._api_client)

    async def close(self) -> None:
        """Close the API client."""
        if self._api_client:
            await self._api_client.close()

    @property
    def core_v1(self) -> CoreV1Api:
        if not self._core_v1:
            raise RuntimeError("Client not connected. Use 'async with' or call connect()")
        return self._core_v1

    @property
    def custom_objects(self) -> CustomObjectsApi:
        if not self._custom_objects:
            raise RuntimeError("Client not connected. Use 'async with' or call connect()")
        return self._custom_objects

    # -------------------------
    # Namespace Operations
    # -------------------------
    async def list_namespaces(self) -> list[str]:
        """List all namespace names."""
        ns_list = await self.core_v1.list_namespace()
        return [ns.metadata.name for ns in ns_list.items]

    async def get_namespace(self, name: str) -> dict[str, Any] | None:
        """Get namespace details."""
        try:
            ns = await self.core_v1.read_namespace(name=name)
            return {
                "name": ns.metadata.name,
                "status": ns.status.phase,
                "labels": ns.metadata.labels or {},
            }
        except client.ApiException as e:
            if e.status == 404:
                return None
            raise

    async def namespace_exists(self, name: str) -> bool:
        """Check if namespace exists."""
        namespaces = await self.list_namespaces()
        return name in namespaces

    # -------------------------
    # Pod Operations
    # -------------------------
    async def list_pods(
        self,
        namespace: str | None = None,
        label_selector: str | None = None,
    ) -> list[dict[str, Any]]:
        """List pods in a namespace with status info."""
        ns = namespace or self.settings.namespace_default
        kwargs: dict[str, Any] = {"namespace": ns}
        if label_selector:
            kwargs["label_selector"] = label_selector
        result = await self.core_v1.list_namespaced_pod(**kwargs)
        return [
            {
                "name": pod.metadata.name,
                "status": pod.status.phase,
                "ready": all(
                    cs.ready for cs in (pod.status.container_statuses or [])
                ),
            }
            for pod in result.items
        ]

    async def get_pod_status(self, name: str, namespace: str | None = None) -> dict[str, Any]:
        """Get detailed pod status."""
        ns = namespace or self.settings.namespace_default
        pod = await self.core_v1.read_namespaced_pod(name=name, namespace=ns)
        return {
            "name": pod.metadata.name,
            "namespace": pod.metadata.namespace,
            "phase": pod.status.phase,
            "conditions": [
                {"type": c.type, "status": c.status} for c in (pod.status.conditions or [])
            ],
            "containers": [
                {
                    "name": cs.name,
                    "ready": cs.ready,
                    "restart_count": cs.restart_count,
                }
                for cs in (pod.status.container_statuses or [])
            ],
        }

    async def wait_for_pod_ready(
        self,
        name: str,
        namespace: str | None = None,
        timeout: int = 300,
    ) -> bool:
        """Wait for a pod to become ready."""
        ns = namespace or self.settings.namespace_default
        start = asyncio.get_event_loop().time()

        while asyncio.get_event_loop().time() - start < timeout:
            try:
                pod = await self.core_v1.read_namespaced_pod(name=name, namespace=ns)
                if pod.status.phase == "Running":
                    conditions = pod.status.conditions or []
                    ready = any(c.type == "Ready" and c.status == "True" for c in conditions)
                    if ready:
                        return True
            except client.ApiException as e:
                if e.status != 404:
                    raise
            await asyncio.sleep(2)

        return False

    # -------------------------
    # Secret Operations
    # -------------------------
    async def get_secret(self, name: str, namespace: str | None = None) -> "V1Secret":
        """Get a secret."""
        ns = namespace or self.settings.namespace_default
        return await self.core_v1.read_namespaced_secret(name=name, namespace=ns)

    async def create_secret(
        self,
        name: str,
        data: dict[str, str],
        namespace: str | None = None,
        secret_type: str = "Opaque",
    ) -> "V1Secret":
        """Create a secret from string data."""
        import base64

        ns = namespace or self.settings.namespace_default
        encoded_data = {k: base64.b64encode(v.encode()).decode() for k, v in data.items()}

        secret = client.V1Secret(
            api_version="v1",
            kind="Secret",
            metadata=client.V1ObjectMeta(name=name, namespace=ns),
            type=secret_type,
            data=encoded_data,
        )
        return await self.core_v1.create_namespaced_secret(namespace=ns, body=secret)

    async def update_secret(
        self,
        name: str,
        data: dict[str, str],
        namespace: str | None = None,
    ) -> "V1Secret":
        """Update an existing secret."""
        import base64

        ns = namespace or self.settings.namespace_default
        encoded_data = {k: base64.b64encode(v.encode()).decode() for k, v in data.items()}

        secret = await self.get_secret(name, ns)
        secret.data = encoded_data
        return await self.core_v1.replace_namespaced_secret(name=name, namespace=ns, body=secret)

    async def secret_exists(self, name: str, namespace: str | None = None) -> bool:
        """Check if a secret exists."""
        ns = namespace or self.settings.namespace_default
        try:
            await self.core_v1.read_namespaced_secret(name=name, namespace=ns)
            return True
        except client.ApiException as e:
            if e.status == 404:
                return False
            raise

    # -------------------------
    # Service Operations
    # -------------------------
    async def list_services(self, namespace: str | None = None) -> list["V1Service"]:
        """List services in a namespace."""
        ns = namespace or self.settings.namespace_default
        result = await self.core_v1.list_namespaced_service(namespace=ns)
        return result.items

    async def get_service_endpoint(
        self,
        name: str,
        namespace: str | None = None,
    ) -> dict[str, Any]:
        """Get service endpoint information."""
        ns = namespace or self.settings.namespace_default
        svc = await self.core_v1.read_namespaced_service(name=name, namespace=ns)
        return {
            "name": svc.metadata.name,
            "namespace": svc.metadata.namespace,
            "type": svc.spec.type,
            "cluster_ip": svc.spec.cluster_ip,
            "ports": [
                {"name": p.name, "port": p.port, "target_port": p.target_port, "protocol": p.protocol}
                for p in svc.spec.ports
            ],
        }

    # -------------------------
    # Custom Resources
    # -------------------------
    async def list_certificates(self, namespace: str | None = None) -> list[dict[str, Any]]:
        """List cert-manager certificates in a namespace."""
        ns = namespace or self.settings.namespace_default
        try:
            result = await self.custom_objects.list_namespaced_custom_object(
                group="cert-manager.io",
                version="v1",
                namespace=ns,
                plural="certificates",
            )
            certs = []
            for item in result.get("items", []):
                conditions = item.get("status", {}).get("conditions", [])
                ready = any(
                    c.get("type") == "Ready" and c.get("status") == "True"
                    for c in conditions
                )
                certs.append({
                    "name": item["metadata"]["name"],
                    "ready": ready,
                    "secret": item["spec"]["secretName"],
                })
            return certs
        except client.ApiException:
            return []

    async def get_certificates(self, namespace: str = "cert-manager") -> list[dict[str, Any]]:
        """Get cert-manager certificates (deprecated, use list_certificates)."""
        return await self.list_certificates(namespace)

    async def get_ingresses(self, namespace: str | None = None) -> list[dict[str, Any]]:
        """Get ingresses."""
        ns = namespace or self.settings.namespace_default
        try:
            networking_v1 = client.NetworkingV1Api(self._api_client)
            result = await networking_v1.list_namespaced_ingress(namespace=ns)
            return [
                {
                    "name": ing.metadata.name,
                    "namespace": ing.metadata.namespace,
                    "hosts": [rule.host for rule in ing.spec.rules] if ing.spec.rules else [],
                    "tls": bool(ing.spec.tls),
                }
                for ing in result.items
            ]
        except client.ApiException:
            return []


@asynccontextmanager
async def kubernetes_client(
    settings: Settings | None = None,
) -> AsyncGenerator[KubernetesClient, None]:
    """Context manager for Kubernetes client."""
    k8s = KubernetesClient(settings)
    try:
        await k8s.connect()
        yield k8s
    finally:
        await k8s.close()
