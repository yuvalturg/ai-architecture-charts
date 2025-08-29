# Configure Pipeline Helm Chart

This Helm chart deploys a configuration pipeline that sets up a Jupyter notebook environment for RAG (Retrieval-Augmented Generation) configuration and MinIO storage.

## Overview

The configure-pipeline chart creates:
- A Jupyter notebook deployment for pipeline configuration
- Persistent volume claims for data storage
- Secrets for MinIO and pipeline configuration
- ConfigMaps for pipeline and RAG configuration

## Prerequisites

- OpenShift cluster
- Helm 3.x
- Access to required container registries
- MinIO instance (can be deployed separately)

## Installation

### Basic Installation

```bash
helm install configure-pipeline ./helm
```

### Custom Installation

```bash
helm install configure-pipeline ./helm \
  --set notebook.repo="https://github.com/your-org/your-rag-repo.git" \
  --set minio.host="your-minio-host" \
  --set minio.bucket_name="your-bucket"
```

### Installation with Custom Namespace

```bash
helm install configure-pipeline ./helm \
  --namespace rag-pipeline \
  --create-namespace
```

## Configuration

### Key Configuration Options

| Parameter | Description | Default |
|-----------|-------------|---------|
| `notebook.create` | Create notebook deployment | `true` |
| `notebook.image` | Notebook container image | `image-registry.openshift-image-registry.svc:5000/redhat-ods-applications/s2i-generic-data-science-notebook:2024.2` |
| `notebook.repo` | Git repository for notebook code | `https://github.com/RHEcosystemAppEng/RAG-Blueprint.git` |
| `notebook.pvcName` | PVC name for notebook storage | `pipeline-vol` |
| `minio.user` | MinIO username | `minio_rag_user` |
| `minio.password` | MinIO password | `minio_rag_password` |
| `minio.host` | MinIO service host | `minio` |
| `minio.port` | MinIO service port | `9000` |
| `minio.region` | MinIO region | `us-east-1` |
| `minio.bucket_name` | MinIO bucket name | `llama` |
| `embedding_model` | Embedding model to use | `all-MiniLM-L6-v2` |
| `name` | RAG vector database name | `rag-vector-db` |
| `version` | Version identifier | `1.0` |

### Example values.yaml

```yaml
notebook:
  create: true
  image: "quay.io/your-org/custom-notebook:latest"
  repo: "https://github.com/your-org/custom-rag-repo.git"
  pvcName: "custom-pipeline-vol"

minio:
  user: custom_user
  password: custom_password
  host: custom-minio-host
  port: 9000
  region: us-west-2
  bucket_name: custom-bucket

embedding_model: sentence-transformers/all-MiniLM-L6-v2
name: custom-rag-db
version: 2.0
```

## Usage

After installation, the chart will create:

1. **Jupyter Notebook**: Access your notebook environment for pipeline configuration
2. **Storage**: Persistent volumes for data persistence  
3. **Secrets**: MinIO credentials and pipeline configuration secrets
4. **ConfigMaps**: Pipeline and RAG configuration

### Accessing the Notebook

The notebook will be available through the Kubernetes service. Port-forward to access:

```bash
oc port-forward svc/configure-pipeline-notebook 8888:8888
```

Then access at `http://localhost:8888`

### OpenShift Route (if available)

On OpenShift, you can create a route for external access:

```bash
oc expose service configure-pipeline-notebook
```

### MinIO Configuration

The chart automatically configures MinIO access with the provided credentials. Ensure your MinIO instance is running and accessible at the specified host and port.

### Pipeline Configuration

The notebook environment includes:
- Pre-configured MinIO access
- RAG pipeline templates
- Embedding model configuration
- Vector database setup scripts

## Monitoring and Troubleshooting

### Checking Pod Status

```bash
oc get pods -l app.kubernetes.io/name=configure-pipeline
```

### Viewing Logs

```bash
oc logs -l app.kubernetes.io/name=configure-pipeline -f
```

### Common Issues

1. **Notebook won't start**: 
   - Check if the specified Git repository is accessible
   - Verify image registry permissions
   - Check resource limits

2. **MinIO connection issues**: 
   - Verify MinIO service is running and accessible
   - Check credentials and network connectivity
   - Validate bucket exists

3. **Storage issues**: 
   - Ensure sufficient storage is available for PVCs
   - Check storage class availability
   - Verify PVC binding

4. **Git repository access**:
   - Ensure repository URL is correct and accessible
   - For private repos, configure authentication
   - Check network policies

### Checking Configuration

```bash
# Check secrets
oc get secrets -l app.kubernetes.io/name=configure-pipeline

# Check configmaps
oc get configmaps -l app.kubernetes.io/name=configure-pipeline

# Check PVCs
oc get pvc -l app.kubernetes.io/name=configure-pipeline
```

## Upgrading

To upgrade the chart:

```bash
helm upgrade configure-pipeline ./helm
```

## Uninstalling

```bash
helm uninstall configure-pipeline
```

**Note**: This will not delete PVCs by default. To also remove persistent data:

```bash
oc delete pvc -l app.kubernetes.io/name=configure-pipeline
```

## Dependencies

- **MinIO instance**: Object storage for documents and models
- **Git repository access**: For notebook code and templates
- **Sufficient cluster resources**: CPU, memory, and storage
- **Container registry access**: For pulling notebook images
- **Network connectivity**: Between components and external services

## Integration

This chart works well with other components in the AI architecture:

- **ingestion-pipeline**: For data processing workflows
- **llama-stack**: For LLM inference capabilities  
- **pgvector**: For vector storage
- **minio**: For object storage

Deploy these components in the same namespace for optimal integration.