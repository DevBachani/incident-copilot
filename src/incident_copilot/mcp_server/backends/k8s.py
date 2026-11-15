"""Read-only Kubernetes access for the log and event tools.

Uses the current kubeconfig context (k3d-incident in dev). In-cluster, the MCP
server would use a read-only ServiceAccount (Phase 5 RBAC).
"""

from __future__ import annotations

from functools import lru_cache

from kubernetes import client, config


@lru_cache
def _core() -> client.CoreV1Api:
    try:
        config.load_kube_config()
    except Exception:  # noqa: BLE001 - fall back to in-cluster config when mounted
        config.load_incluster_config()
    return client.CoreV1Api()


def _pod_name(pod: object) -> str:
    meta = getattr(pod, "metadata", None)
    return getattr(meta, "name", "") or ""


def _pod_for_service(namespace: str, service: str) -> str | None:
    pods = _core().list_namespaced_pod(namespace, label_selector=f"app={service}")
    if not pods.items:
        return None
    # Prefer a running pod; otherwise the first (may be crashing).
    for pod in pods.items:
        if pod.status and pod.status.phase == "Running":
            return _pod_name(pod)
    return _pod_name(pods.items[0])


def read_pod_logs(
    namespace: str, service: str, previous: bool = False, tail_lines: int = 40
) -> tuple[str, list[str]]:
    pod = _pod_for_service(namespace, service)
    if pod is None:
        return "", [f"no pod found for app={service} in ns {namespace}"]
    try:
        raw = _core().read_namespaced_pod_log(
            name=pod, namespace=namespace, previous=previous, tail_lines=tail_lines
        )
    except client.ApiException as exc:
        return pod, [f"could not read logs: {exc.reason}"]
    return pod, [ln for ln in raw.splitlines() if ln.strip()]


def list_warning_events(namespace: str, limit: int = 20) -> list[dict[str, object]]:
    events = _core().list_namespaced_event(namespace)
    warnings = [e for e in events.items if e.type == "Warning"]
    warnings.sort(key=lambda e: e.last_timestamp or e.event_time or 0, reverse=True)
    out: list[dict[str, object]] = []
    for e in warnings[:limit]:
        out.append(
            {
                "type": e.type,
                "reason": e.reason or "",
                "object": f"{e.involved_object.kind}/{e.involved_object.name}",
                "message": (e.message or "")[:200],
                "count": e.count or 1,
                "last_seen": str(e.last_timestamp) if e.last_timestamp else None,
            }
        )
    return out
