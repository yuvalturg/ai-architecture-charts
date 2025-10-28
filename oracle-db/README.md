# Oracle 23ai Unified Helm Chart

A comprehensive Helm chart for deploying Oracle 23ai Database with optional TPC-DS data loading in Kubernetes/OpenShift environments.

## 🚀 Features

- **Single Command Deployment**: Complete Oracle 23ai setup with one `helm install`
- **Intelligent Readiness Detection**: Log-based Oracle initialization monitoring
- **Flexible Data Loading**: Optional TPC-DS benchmark data population
- **Production Ready**: Secure password management and robust error handling
- **Enterprise Compatible**: RBAC, Security Context Constraints, and proper resource management

## 📁 Project Structure

```
oracle-db/
├── README.md                    # Project overview
├── README-UNIFIED-HELM.md       # This documentation
└── helm/                # Complete Helm solution
    ├── Chart.yaml              # Chart metadata
    ├── values.yaml              # Configuration options
    └── templates/               # Kubernetes manifests
        ├── _helpers.tpl         # Template helpers
        ├── oracle-statefulset.yaml  # Oracle Database deployment
        ├── oracle-service.yaml      # Database service
        ├── oracle-secret.yaml       # Credential management
        ├── oracle-serviceaccount.yaml # Service account
        ├── oracle-scc.yaml          # Security constraints
        ├── tpcds-job.yaml           # Data loading job
        └── tpcds-rbac.yaml          # RBAC for data loader
```

## 🎯 Quick Start

### Basic Installation (Database Only)
```bash
# Install Oracle 23ai database only
helm install oracle-db helm/ \
  --namespace oracle-db \
  --create-namespace \
  --set tpcds.enabled=false
```

### Full Installation (Database + TPC-DS Data)
```bash
# Install Oracle 23ai with TPC-DS data loading
helm install oracle-db helm/ \
  --namespace oracle-db \
  --create-namespace
```

### Custom Configuration
```bash
# Install with custom settings
helm install oracle-db helm/ \
  --namespace oracle-db \
  --create-namespace \
  --set oracle.secret.password="MySecurePassword123!" \
  --set tpcds.scaleFactor=2 \
  --set tpcds.parallel=4
```

## 🎛️ Configuration Options

### Installation Control
```yaml
installation:
  installDB: true        # Deploy Oracle database
  waitForDbReadiness: true # Enable comprehensive readiness checks
```

### Oracle Database Configuration
```yaml
oracle:
  image:
    repository: container-registry.oracle.com/database/free
    tag: "latest"
  
  secret:
    password: ""  # Auto-generated if empty
    host: oracle-db
    port: "1521"
    serviceName: "freepdb1"
  
  resources:
    requests:
      memory: "2Gi"
      cpu: "1"
    limits:
      memory: "4Gi"
      cpu: "2"
  
  probes:
    readiness:
      initialDelaySeconds: 180  # Allow Oracle startup time
      periodSeconds: 60        # Check every minute
      failureThreshold: 20     # Up to 20 minutes for initialization
```

### TPC-DS Data Loading Configuration
```yaml
tpcds:
  enabled: true           # Enable data loading - installs both loader infrastructure and loads data
  scaleFactor: 1          # Data volume (1 = ~1GB)
  parallel: 2             # Parallel loading workers
  schemaName: "SYSTEM"    # Target schema
  
  job:
    backoffLimit: 2
    activeDeadlineSeconds: 3600  # 1 hour timeout
    
    resources:
      tpcdsPopulate:
        requests:
          memory: "1Gi"
          cpu: "1"
        limits:
          memory: "2Gi"
          cpu: "2"
```

## 📊 Deployment Scenarios

### 1. Database Only
Perfect for when you have existing data or want to load custom datasets:

```yaml
# values-db-only.yaml
installation:
  installDB: true

tpcds:
  enabled: false
```

```bash
helm install oracle-db helm/ -f values-db-only.yaml -n oracle-db --create-namespace
```

### 2. Database + TPC-DS Data (Default)
Complete setup with benchmark data for testing and development:

```bash
helm install oracle-complete helm/ -n oracle-db --create-namespace
```

### 3. Data Loading to Existing Database
Load TPC-DS data into an already running Oracle instance:

```yaml
# values-loader-only.yaml
installation:
  installDB: false

tpcds:
  enabled: true
  database:
    host: existing-oracle-service
    existingSecret: existing-oracle-secret
```

```bash
helm install tpcds-loader helm/ -f values-loader-only.yaml -n oracle-db
```

## 🔍 Monitoring and Verification

### Check Installation Progress
```bash
# Overall status
helm status oracle-db -n oracle-db

# Watch pods
oc get pods -n oracle-db -w

# Check Oracle logs
oc logs -f oracle-db-0 -n oracle-db

# Check TPC-DS data loading
oc logs -f job/oracle-db-tpcds-populate -n oracle-db
```

### Database Connection
```bash
# Get generated password
oc get secret oracle-db -n oracle-db -o jsonpath='{.data.password}' | base64 -d

# Port forward for external access
oc port-forward svc/oracle-db 1521:1521 -n oracle-db

# Connect using sqlplus or any Oracle client
sqlplus system/<password>@localhost:1521/freepdb1
```

### Verify TPC-DS Data
```bash
# Check if data was loaded successfully
oc exec oracle-db-0 -n oracle-db -- sqlplus -s system/<password>@localhost:1521/freepdb1 <<EOF
SELECT table_name, num_rows FROM user_tables WHERE table_name LIKE '%STORE%';
EXIT;
EOF
```

## 🔧 Advanced Configuration

### Custom Oracle Settings
```yaml
oracle:
  env:
    - name: ORACLE_PWD
      valueFrom:
        secretKeyRef:
          key: password
          name: oracle-db
    - name: ORACLE_CHARACTERSET
      value: "AL32UTF8"
    - name: ENABLE_ARCHIVELOG
      value: "true"
  
  ai:
    vectorMemoryTarget: "1G"
    enableVectorIndex: true
    enableJsonDuality: true
```

### Development Environment
```yaml
# values-dev.yaml - Faster startup for development
oracle:
  probes:
    readiness:
      initialDelaySeconds: 60
      failureThreshold: 10

tpcds:
  scaleFactor: 0.1  # Smaller dataset
  parallel: 1
```

### Production Environment
```yaml
# values-prod.yaml - Production settings
oracle:
  resources:
    requests:
      memory: "8Gi"
      cpu: "4"
    limits:
      memory: "16Gi"
      cpu: "8"

tpcds:
  scaleFactor: 10
  parallel: 8
  
  job:
    activeDeadlineSeconds: 7200  # 2 hours
```

## 🔒 Security Features

- **Automatic Password Generation**: Secure 16-character passwords
- **Password Stability**: No regeneration on Helm upgrades
- **RBAC**: Minimal required permissions for data loader
- **SCC Support**: OpenShift Security Context Constraints
- **Secret Management**: Kubernetes-native credential storage

## 🚨 Troubleshooting

### Common Issues

**Oracle Pod Not Ready**
```bash
# Check Oracle logs for initialization issues
oc logs oracle-db-0 -n oracle-db

# Increase readiness probe timeout
helm upgrade oracle-db helm/ --set oracle.probes.readiness.failureThreshold=30
```

**TPC-DS Job Fails**
```bash
# Check init container logs
oc logs <tpcds-pod> -c wait-for-oracle-complete-readiness -n oracle-db

# Check main container logs
oc logs <tpcds-pod> -c tpcds-populate -n oracle-db
```

**Permission Denied**
```bash
# Ensure SCC is created (OpenShift)
oc get scc oracle-db-scc

# Check service account permissions
oc describe rolebinding oracle-db-tpcds-binding -n oracle-db
```

## 🗑️ Cleanup

### Complete Uninstall
```bash
# Remove Helm release
helm uninstall oracle-db -n oracle-db

# Clean up persistent data
oc delete pvc --all -n oracle-db

# Remove namespace
oc delete namespace oracle-db

# Remove SCC (OpenShift)
oc delete scc oracle-db-scc
```

### Partial Cleanup (Keep Database)
```bash
# Remove only TPC-DS components
helm upgrade oracle-db helm/ --set tpcds.enabled=false
```

## 📈 Performance Tuning

### Oracle Database
- Adjust memory settings in `oracle.resources`
- Configure `oracle.ai.vectorMemoryTarget` for AI workloads
- Enable archivelog for production: `ENABLE_ARCHIVELOG=true`

### TPC-DS Loading
- Increase `tpcds.parallel` for faster loading
- Adjust `tpcds.job.resources` based on available cluster capacity
- Use appropriate `scaleFactor` for your testing needs

## 🔗 Integration Examples

### With Monitoring (Prometheus)
```yaml
oracle:
  monitoring:
    enabled: true
    exporterImage: "iamseth/oracledb_exporter:latest"
    serviceMonitor:
      enabled: true
```

### With Custom Init Scripts
```yaml
oracle:
  initdb:
    enabled: true
    scripts:
      - |
        CREATE USER myapp IDENTIFIED BY mypassword;
        GRANT CONNECT, RESOURCE TO myapp;
```

---

## 🎉 Success!

You now have a production-ready Oracle 23ai deployment with optional TPC-DS data loading, all managed through standard Kubernetes/Helm tooling. The chart provides enterprise-grade features while maintaining simplicity for development use cases.

For questions or issues, check the troubleshooting section above or review the Helm chart templates for detailed implementation.