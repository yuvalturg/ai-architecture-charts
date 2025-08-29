# LlamaStack Helm Chart

This Helm chart deploys LlamaStack, a comprehensive inference and API server that supports multiple LLM providers including Meta's Llama models, remote vLLM endpoints, VertexAI, and other model providers with support for embeddings and AI agent capabilities.

## Overview

The llama-stack chart creates:
- LlamaStack deployment with configurable models
- Service for API access
- ConfigMap for runtime configuration
- PVC for model storage and cache
- Secret management for external providers
- Support for VertexAI, local models, and MCP servers

## Prerequisites

- OpenShift cluster
- Helm 3.x
- Access to model repositories (HuggingFace, etc.)
- External dependencies:
  - PGVector database for vector storage
  - LLM Service deployment for model inference (if using local models)

## Installation

### Basic Installation

```bash
helm install llama-stack ./helm
```

### Installation with VertexAI Support

**Important**: VertexAI requires a Google Cloud service account file. You must provide this file during installation:

```bash
helm install llama-stack ./helm \
  --set vertexai.enabled=true \
  --set vertexai.projectId=your-gcp-project \
  --set vertexai.location=us-central1 \
  --set-file gcpServiceAccountFile=path/to/service-account.json
```

The service account file will be mounted at `/var/secrets/gcp-service-account.json` inside the container.

### Installation with Local Models

```bash
helm install llama-stack ./helm \
  --set models.llama-3-2-3b-instruct.enabled=true \
  --set models.llama-guard-3-8b.enabled=true
```

**Note**: When enabling models without providing a `url`, LlamaStack assumes the models are served by the LLM Service in the same namespace. The chart automatically generates URLs pointing to `{model-name}-predictor.{namespace}.svc.cluster.local:8080/v1`.

## Configuration

### Key Configuration Options

| Parameter | Description | Default |
|-----------|-------------|---------|
| `replicaCount` | Number of replicas | `1` |
| `rawDeploymentMode` | Use raw Deployment instead of other controllers | `true` |
| `image.repository` | Container image repository | `llamastack/distribution-starter` |
| `image.pullPolicy` | Image pull policy | `IfNotPresent` |
| `service.port` | Service port | `8321` |
| `progressDeadlineSeconds` | Deployment progress deadline | `3600` |
| `strategy.type` | Deployment strategy | `Recreate` |
| `vertexai.enabled` | Enable VertexAI provider | `false` |
| `vertexai.projectId` | Google Cloud project ID for VertexAI | `""` |
| `vertexai.location` | Google Cloud region/location for VertexAI | `""` |
| `gcpServiceAccount.name` | GCP service account secret name | `gcp-service-account` |
| `gcpServiceAccount.mountPath` | Path where GCP service account is mounted | `/var/secrets/gcp-service-account.json` |
| `gcpServiceAccountFile` | GCP service account file (use --set-file) | `""` |

### Model Configuration

The chart supports multiple models that can be enabled/disabled. Models can be served by:
1. **Local LLM Service** (same namespace) - no URL needed, automatically generated
2. **Remote vLLM endpoints** - provide explicit URL
3. **VertexAI** - Google Cloud hosted models

```yaml
models:
  # Local model (served by LLM Service in same namespace)
  llama-3-2-3b-instruct:
    id: meta-llama/Llama-3.2-3B-Instruct
    enabled: true
    # No URL needed - auto-generated as:
    # http://llama-3-2-3b-instruct-predictor.{namespace}.svc.cluster.local:8080/v1
  
  # Safety model registered as a shield
  llama-guard-3-8b:
    id: meta-llama/Llama-Guard-3-8B
    enabled: true
    url: "http://remote-vllm-service:8000/v1"
    registerShield: true  # Registers this model as a safety shield
  
  # Another local model
  llama-3-1-8b-instruct:
    id: meta-llama/Llama-3.1-8B-Instruct
    enabled: false
```

### Safety Shields with registerShield

The `registerShield: true` parameter registers a model as a **safety shield** in LlamaStack. Safety shields are specialized models (typically Llama Guard variants) that provide content moderation and safety filtering capabilities:

- **Input filtering**: Analyzes user prompts for harmful content before processing
- **Output filtering**: Reviews model responses for safety violations before returning to users
- **Content categories**: Detects violence, hate speech, sexual content, self-harm, and other harmful categories
- **Automatic integration**: Once registered, shields are automatically applied to inference requests

Example safety shield configuration:
```yaml
models:
  llama-guard-3-1b:
    id: meta-llama/Llama-Guard-3-1B
    enabled: true
    registerShield: true  # This model will act as a safety filter
  
  llama-guard-3-8b:
    id: meta-llama/Llama-Guard-3-8B  
    enabled: true
    registerShield: true  # Multiple shields can be registered
    
  # Regular inference model (not a shield)
  llama-3-2-3b-instruct:
    id: meta-llama/Llama-3.2-3B-Instruct
    enabled: true
    # registerShield: false (default)
```

**Best Practices**:
- Use safety/moderation models as shields (e.g., Llama Guard, but any safety model works)
- Register multiple shield models for redundancy
- Only set `registerShield: true` for safety/moderation models
- Regular inference models should not be registered as shields

### VertexAI Configuration

For Google Cloud VertexAI integration, you **must** provide a service account file:

```yaml
vertexai:
  enabled: true
  projectId: your-gcp-project-id
  location: us-central1

gcpServiceAccount:
  name: gcp-service-account
  mountPath: /var/secrets/gcp-service-account.json
```

**Required**: Use `--set-file gcpServiceAccountFile=path/to/service-account.json` during installation to provide the GCP service account credentials. Without this file, VertexAI integration will not work.

### Environment Variables

```yaml
env:
  - name: OTEL_ENDPOINT
    value: http://otel-collector-collector.observability-hub.svc.cluster.local:4318/v1/traces
  - name: POSTGRES_USER
    valueFrom:
      secretKeyRef:
        key: user
        name: pgvector
  - name: POSTGRES_PASSWORD
    valueFrom:
      secretKeyRef:
        key: password
        name: pgvector
```

### Storage Configuration

```yaml
volumes:
  - configMap:
      defaultMode: 420
      name: run-config
    name: run-config-volume
  - name: dot-llama
    persistentVolumeClaim:
      claimName: llama-stack-data
  - emptyDir: {}
    name: cache

volumeMounts:
  - mountPath: /app-config
    name: run-config-volume
  - mountPath: /.llama
    name: dot-llama
  - mountPath: /.cache
    name: cache
```

### Complete Example values.yaml

```yaml
replicaCount: 1
rawDeploymentMode: true

image:
  repository: llamastack/distribution-starter
  pullPolicy: IfNotPresent

service:
  type: ClusterIP
  port: 8321

# Enable VertexAI
vertexai:
  enabled: true
  projectId: my-gcp-project
  location: us-central1

# Enable specific models
models:
  llama-3-2-3b-instruct:
    enabled: true
  llama-guard-3-8b:
    enabled: true
    registerShield: true

# Resource limits
resources:
  requests:
    memory: "4Gi"
    cpu: "1000m"
  limits:
    memory: "8Gi"
    cpu: "2000m"

# Agent provider configuration
providers:
  agents:
    - provider_id: meta-reference
      provider_type: inline::meta-reference
      config:
        persistence_store:
          type: sqlite
          db_path: ${env.SQLITE_STORE_DIR:=~/.llama/distributions/starter}/agents_store.db
```

## Usage

### Accessing the API

The LlamaStack API is available on port 8321:

```bash
# Port forward for local access
oc port-forward svc/llama-stack 8321:8321

# Test the API
curl http://localhost:8321/models
```

### OpenShift Route

Create a route for external access:

```bash
oc expose service llama-stack
oc get routes llama-stack
```

### API Examples

#### List Available Models
```bash
curl -X GET http://localhost:8321/models
```

#### Generate Text Completion
```bash
curl -X POST http://localhost:8321/inference/completion \
  -H "Content-Type: application/json" \
  -d '{
    "model_id": "llama-3-2-3b-instruct",
    "content": {
      "type": "text",
      "text": "What is artificial intelligence?"
    }
  }'
```

#### Create Embeddings
```bash
curl -X POST http://localhost:8321/inference/embeddings \
  -H "Content-Type: application/json" \
  -d '{
    "model_id": "llama-3-2-3b-instruct",
    "contents": ["Hello world", "How are you?"]
  }'
```

### Integration with Vector Database

LlamaStack integrates with PGVector for storing embeddings:

```bash
# Check database connection
oc exec -it deployment/llama-stack -- env | grep POSTGRES
```

## Monitoring and Troubleshooting

### Checking Service Health

```bash
# Check pod status
oc get pods -l app.kubernetes.io/name=llama-stack

# Check service
oc get svc llama-stack

# Test health endpoint
oc exec -it deployment/llama-stack -- curl localhost:8321/health
```

### Viewing Logs

```bash
# Service logs
oc logs -l app.kubernetes.io/name=llama-stack -f

# Previous container logs (if crashed)
oc logs -l app.kubernetes.io/name=llama-stack --previous

# Check specific container logs
oc logs deployment/llama-stack -c llama-stack -f
```

### Common Issues

1. **Model Download Failures**:
   - Check internet connectivity
   - Verify HuggingFace access tokens
   - Ensure sufficient storage space
   - Check model permissions

2. **VertexAI Connection Issues**:
   - Verify GCP service account credentials
   - Check project ID and location settings
   - Validate API permissions
   - Ensure VertexAI APIs are enabled

3. **Memory/Storage Issues**:
   - Models require significant storage and memory
   - Check PVC size and availability
   - Monitor resource usage
   - Consider using smaller models for testing

4. **Database Connection Errors**:
   - Verify PGVector is running
   - Check database credentials in secrets
   - Validate network connectivity
   - Test database schema compatibility

5. **Model Endpoint Issues**:
   - Ensure LLM Service is deployed in same namespace (for local models)
   - Verify model predictor services are running
   - Check if model URLs are accessible
   - Validate model configuration in LLM Service

### Resource Requirements

LlamaStack is a lightweight orchestration layer and doesn't require GPU resources:

```yaml
# Typical LlamaStack resource requirements
resources:
  requests:
    memory: "1Gi"
    cpu: "500m"
  limits:
    memory: "2Gi"
    cpu: "1000m"
```

**Note**: Model inference resources are managed by the LLM Service component, not LlamaStack.

## Security and Authentication

### Custom Authentication

Configure custom authentication provider:

```yaml
auth:
  provider_config:
    type: "custom"
    endpoint: "https://auth.example.com/validate"
  access_policy:
    - permit:
        actions: [create]
        resource: session::*
      description: all users have create access to sessions
    - permit:
        actions: [read]
        resource: model::*
      description: all users have read access to models
```

### Service Account Security

The chart creates minimal RBAC permissions:
- ConfigMap read access
- Secret read access
- PVC read/write access

## Upgrading

```bash
# Upgrade with new image version
helm upgrade llama-stack ./helm \
  --set image.tag=v0.3.0

# Check rollout status
oc rollout status deployment/llama-stack
```

## Uninstalling

```bash
# Remove chart
helm uninstall llama-stack

# Remove persistent data
oc delete pvc llama-stack-data

# Remove secrets (if needed)
oc delete secret gcp-service-account
```

## Integration with Other Components

This chart integrates with:

- **LLM Service**: Deploy and serve models locally in the same namespace. LlamaStack automatically discovers and configures models deployed by the LLM Service chart
- **PGVector**: Vector database for embeddings and agent memory
- **MinIO**: Model and data storage
- **Ingestion Pipeline**: Document processing workflows
- **VertexAI**: Google Cloud AI services
- **MCP Servers**: External tool integration

### LlamaStack + LLM Service Integration

LlamaStack works seamlessly with the LLM Service chart to provide a complete model serving solution:

```bash
# 1. Deploy models using LLM Service
helm install llm-service ../llm-service/helm \
  --set models.llama-3-2-3b-instruct.enabled=true \
  --set models.llama-guard-3-8b.enabled=true

# 2. Deploy LlamaStack and configure it to use the deployed models
helm install llama-stack ./helm \
  --set models.llama-3-2-3b-instruct.enabled=true \
  --set models.llama-guard-3-8b.enabled=true \
  --set models.llama-guard-3-8b.registerShield=true
```

**How it works**:
- LLM Service deploys models as InferenceServices with predictors
- LlamaStack automatically generates URLs pointing to these predictors
- Model URLs follow the pattern: `{model-name}-predictor.{namespace}.svc.cluster.local:8080/v1`
- LlamaStack provides unified API access and orchestration layer
- Safety shields and agent capabilities are handled by LlamaStack
- Model inference is handled by LLM Service/vLLM

**Benefits of this approach**:
- **Separation of concerns**: LLM Service handles model deployment, LlamaStack handles orchestration
- **Automatic discovery**: No manual URL configuration needed for local models
- **Unified API**: Single endpoint for multiple models and capabilities
- **Safety integration**: Automatic shield model integration
- **Agent capabilities**: Advanced AI agent features through LlamaStack

### LlamaStack + PGVector Integration

LlamaStack can be deployed with the PGVector component from this repository to provide persistent vector storage for embeddings, agent memory, and RAG capabilities:

```bash
# 1. Deploy PGVector using the pgvector chart from this repo
helm install pgvector ../pgvector/helm \
  --set secret.dbname=llamastack_vectors \
  --set extraDatabases[0].name=agent_memory \
  --set extraDatabases[0].vectordb=true

# 2. Deploy LlamaStack configured to use the PGVector deployment
helm install llama-stack ./helm \
  --set models.llama-3-2-3b-instruct.enabled=true
  # PGVector connection is automatically configured via environment variables
```

**How it works**:
- The PGVector chart from this repo creates a PostgreSQL deployment with pgvector extension
- LlamaStack automatically connects using the `pgvector` secret created by the PGVector chart
- Environment variables (`POSTGRES_USER`, `POSTGRES_PASSWORD`, etc.) are automatically configured
- LlamaStack uses PGVector for vector storage, agent memory, and RAG operations

**What LlamaStack stores in PGVector**:
- **Vector embeddings**: Document and text embeddings for RAG
- **Agent memory**: Persistent memory for AI agents across sessions
- **Knowledge base**: Long-term storage of facts and learned information
- **Session context**: Conversation history and multi-turn interactions

## Advanced Configuration

### MCP Servers Integration

```yaml
mcp-servers:
  weather-server:
    endpoint: "http://mcp-weather:8000/sse"
    capabilities: ["weather_lookup"]
```

### Custom Model Providers

```yaml
providers:
  inference:
    - provider_id: custom-vllm
      provider_type: remote::vllm
      config:
        url: "http://custom-vllm-service:8000/v1"
```

### Observability Integration

```yaml
env:
  - name: OTEL_ENDPOINT
    value: "http://jaeger-collector:14268/api/traces"
  - name: OTEL_SERVICE_NAME
    value: "llama-stack"
```