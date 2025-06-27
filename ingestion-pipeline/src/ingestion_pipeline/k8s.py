import base64
import re

from kubernetes import client, config

from .models import BaseSourceModel


def normalize_name(name: str, max_length: int = 253) -> str:
    name = name.lower()
    name = re.sub(r'[^a-z0-9-]', '-', name)
    name = re.sub(r'-+', '-', name)
    if len(name) > max_length:
        name = name[:max_length].rstrip('-')
    name = re.sub(r'^[^a-z0-9]+', '', name)
    name = re.sub(r'[^a-z0-9]+$', '', name)
    return name


def get_incluster_namespace(default: str = "default") -> str:
    try:
        with open("/var/run/secrets/kubernetes.io/serviceaccount/namespace") as f:
            return f.read().strip()
    except Exception:
        return default


def model_to_k8s_secret(model: BaseSourceModel, namespace: str = None) -> client.V1Secret:
    namespace = namespace or get_incluster_namespace()

    encoded_data = {
        k.upper(): base64.b64encode(str(v).encode()).decode()
        for k, v in model.model_dump().items()
    }

    return client.V1Secret(
        api_version="v1",
        kind="Secret",
        metadata=client.V1ObjectMeta(
            name=normalize_name(model.pipeline_name()),
            namespace=namespace
        ),
        type="Opaque",
        data=encoded_data,
    )


def apply_model_as_secret(model: BaseSourceModel, namespace: str = None, replace: bool = False) -> str:
    try:
        config.load_incluster_config()
    except config.config_exception.ConfigException:
        config.load_kube_config()

    secret = model_to_k8s_secret(model, namespace)

    api = client.CoreV1Api()
    try:
        api.create_namespaced_secret(
            namespace=secret.metadata.namespace,
            body=secret
        )
        return secret.metadata.name
    except client.exceptions.ApiException as e:
        if e.status == 409 and replace:
            api.replace_namespaced_secret(
                name=secret.metadata.name,
                namespace=secret.metadata.namespace,
                body=secret
            )
            return secret.metadata.name
        else:
            raise


def delete_k8s_secret(secret_name: str, namespace: str = None) -> bool:
    try:
        config.load_incluster_config()
    except config.config_exception.ConfigException:
        config.load_kube_config()

    namespace = namespace or get_incluster_namespace()

    api = client.CoreV1Api()
    try:
        api.delete_namespaced_secret(name=secret_name, namespace=namespace)
        return True
    except client.exceptions.ApiException as e:
        import traceback
        traceback.print_exc()
        return False
