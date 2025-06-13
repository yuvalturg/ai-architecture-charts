import base64

from kubernetes import client, config

from .models import BaseSourceModel


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
        metadata=client.V1ObjectMeta(name=model.k8s_name(), namespace=namespace),
        type="Opaque",
        data=encoded_data,
    )

def apply_model_as_secret(model: BaseSourceModel, namespace: str = None, replace: bool = False):
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
    except client.exceptions.ApiException as e:
        if e.status == 409 and replace:
            api.replace_namespaced_secret(
                name=secret.metadata.name,
                namespace=secret.metadata.namespace,
                body=secret
            )
        else:
            raise
