# Oracle 23ai Unified Helm Chart

A comprehensive Helm chart for deploying Oracle 23ai Database with automatic user management and optional TPC-DS data loading in Kubernetes/OpenShift environments.

## 🚀 Features

- **Automatic User Management**: Schema owners and read-only users with auto-generated passwords
- **Single Command Deployment**: Complete Oracle 23ai setup with one `helm install`
- **Flexible Data Loading**: Optional TPC-DS benchmark data population
- **Production Ready**: Secure password management via Kubernetes secrets
- **Enterprise Compatible**: RBAC, Security Context Constraints, and proper resource management

## 📁 Project Structure

```
oracle-db/
├── README.md                           # This documentation
├── helm/                               # Helm chart
│   ├── Chart.yaml                      # Chart metadata
│   ├── values.yaml                     # Configuration options
│   ├── files/
│   │   └── manage-users.sh             # User management script
│   └── templates/                      # Kubernetes manifests
│       ├── _helpers.tpl                # Template helpers
│       ├── oracle-statefulset.yaml     # Oracle database + user-manager sidecar
│       ├── oracle-service.yaml         # Database service
│       ├── oracle-user-secrets.yaml    # Per-user credentials
│       ├── oracle-user-scripts-configmap.yaml  # User management ConfigMap
│       ├── oracle-serviceaccount.yaml  # Service account
│       ├── oracle-scc.yaml             # Security constraints
│       └── tpcds-job.yaml              # TPC-DS data loading job
└── tpcds-util/                         # TPC-DS data generation tool
    └── src/tpcds_util/                 # Python package
```

## 🎯 Quick Start

### Basic Installation (Database Only)
```bash
# Install Oracle 23ai database with automatic user management
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
  --set tpcds.scaleFactor=2 \
  --set tpcds.parallel=4
```

## 🎛️ Configuration Options

### User Management

The chart automatically creates database users with auto-generated passwords stored in Kubernetes secrets:

```yaml
oracle:
  users:
    - name: system
      schema: system
      mode: rw
      description: "Oracle SYSTEM administrator account"
    - name: sales
      schema: sales
      mode: rw
      description: "Sales schema owner for TPC-DS data"
    - name: sales_reader
      schema: sales
      mode: ro
      description: "Read-only alias for AI/MCP servers"
```

**User Modes:**
- `rw` (read-write): Full schema privileges including CREATE TABLE, CREATE VIEW, INSERT, UPDATE, DELETE
- `ro` (read-only): SELECT privileges only

**Secrets Created:**
- `oracle-db-user-system` - System administrator credentials
- `oracle-db-user-sales` - Sales schema owner credentials
- `oracle-db-user-sales-reader` - Read-only user credentials

Each secret contains:
- `username` - Database username
- `password` - Auto-generated 16-character password (preserved across Helm upgrades)
- `schema` - Target schema name
- `host`, `port`, `serviceName` - Connection details
- `jdbc-uri`, `connection-string` - Pre-formatted connection strings

### Oracle Database Configuration

```yaml
oracle:
  image:
    repository: container-registry.oracle.com/database/free
    tag: "23.5.0.0"

  connection:
    host: oracle-db
    port: "1521"
    serviceName: "freepdb1"  # Pluggable database
    sid: "FREE"              # Container database

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
      periodSeconds: 60         # Check every minute
      failureThreshold: 20      # Up to 20 minutes
    liveness:
      initialDelaySeconds: 300
      periodSeconds: 120
      timeoutSeconds: 30
```

### TPC-DS Data Loading Configuration

```yaml
tpcds:
  enabled: true           # Enable TPC-DS data loading
  user: sales            # Which user loads the data (must have mode: rw)
  scaleFactor: 1         # Data volume (1 = ~1GB)
  parallel: 2            # Parallel loading workers

  job:
    backoffLimit: 2
    activeDeadlineSeconds: 3600  # 1 hour timeout
```

## 📊 Deployment Architecture

### Component Flow

1. **Oracle StatefulSet**
   - Main oracle-db container runs Oracle 23ai
   - User-manager sidecar creates database users after Oracle is ready

2. **User Creation Process**
   - Wait for Oracle database to be ready
   - Create schema owners (where username == schema)
   - Create alias users (where username != schema) with permissions

3. **TPC-DS Data Loading** (if enabled)
   - Wait for Oracle + user creation to complete
   - Configure tpcds-util with sales user credentials
   - Generate synthetic TPC-DS data
   - Create tables and load data into sales schema

### Environment Variables

All Oracle-related environment variables use the `ORACLE_*` prefix:

- `ORACLE_USER` - Database username
- `ORACLE_PWD` - Database password
- `ORACLE_HOST` - Database host
- `ORACLE_PORT` - Database port
- `ORACLE_SERVICE` - Service name (e.g., freepdb1)

## 🔍 Monitoring and Verification

### Check Installation Progress

```bash
# Overall status
helm status oracle-db -n oracle-db

# Watch pods
oc get pods -n oracle-db -w

# Check Oracle logs
oc logs -f oracle-db-0 -c oracle-db -n oracle-db

# Check user management
oc logs -f oracle-db-0 -c user-manager -n oracle-db

# Check TPC-DS data loading
oc logs -f job/oracle-db-tpcds-populate -n oracle-db
```

### Database Connection

```bash
# Get sales user password
oc get secret oracle-db-user-sales -n oracle-db -o jsonpath='{.data.password}' | base64 -d

# Port forward for external access
oc port-forward svc/oracle-db 1521:1521 -n oracle-db

# Connect using sqlplus
sqlplus sales/<password>@localhost:1521/freepdb1
```

### Verify TPC-DS Data

```bash
# Check if data was loaded successfully
oc exec oracle-db-0 -n oracle-db -- sqlplus -s sales/<password>@localhost:1521/freepdb1 <<EOF
SELECT table_name, num_rows FROM user_tables ORDER BY table_name;
EXIT;
EOF
```

## 🔧 Advanced Configuration

### Custom Users

Add additional users by extending the `oracle.users` list:

```yaml
oracle:
  users:
    - name: system
      schema: system
      mode: rw
    - name: sales
      schema: sales
      mode: rw
    - name: sales_reader
      schema: sales
      mode: ro
    - name: analytics
      schema: analytics
      mode: rw
      description: "Analytics schema owner"
    - name: analytics_reader
      schema: analytics
      mode: ro
      description: "Analytics read-only user"
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
  scaleFactor: 1
  parallel: 2
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

- **Automatic Password Generation**: Secure 16-character random passwords
- **Password Stability**: Preserved across Helm upgrades using Kubernetes `lookup` function
- **Per-User Secrets**: Each user gets dedicated Kubernetes secret
- **Least Privilege**: Read-only users have SELECT-only permissions
- **SCC Support**: OpenShift Security Context Constraints
- **No Hardcoded Credentials**: All credentials managed via Kubernetes secrets

## 🚨 Troubleshooting

### Common Issues

**Oracle Pod Not Ready**
```bash
# Check Oracle container logs
oc logs oracle-db-0 -c oracle-db -n oracle-db

# Check user-manager sidecar logs
oc logs oracle-db-0 -c user-manager -n oracle-db

# Increase readiness probe timeout
helm upgrade oracle-db helm/ --set oracle.probes.readiness.failureThreshold=30
```

**User Creation Fails**
```bash
# Check user-manager sidecar logs
oc logs oracle-db-0 -c user-manager -n oracle-db

# Verify secrets exist
oc get secrets -n oracle-db | grep oracle-db-user

# Check secret content
oc get secret oracle-db-user-sales -n oracle-db -o yaml
```

**TPC-DS Job Fails**
```bash
# Check init container logs
oc logs <tpcds-pod> -c wait-for-oracle -n oracle-db

# Check main container logs
oc logs <tpcds-pod> -c tpcds-populate -n oracle-db

# Check if sales user was created
oc exec oracle-db-0 -n oracle-db -- sqlplus -s system/<password>@localhost:1521/freepdb1 <<EOF
SELECT username FROM dba_users WHERE username = 'SALES';
EXIT;
EOF
```

**Permission Denied**
```bash
# Ensure SCC is created (OpenShift)
oc get scc oracle-db-scc

# Check service account
oc describe sa oracle-db -n oracle-db
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
- Configure `ORACLE_CHARACTERSET` and `ORACLE_EDITION` in env
- Enable archivelog: `ENABLE_ARCHIVELOG=true`

### TPC-DS Loading
- Increase `tpcds.parallel` for faster loading (up to available CPU cores)
- Adjust `tpcds.job.resources` based on cluster capacity
- Use appropriate `scaleFactor` for your testing needs (1 = ~1GB)

## 🔗 Integration with MCP Servers

The oracle-sqlcl MCP server can connect using the auto-generated secrets:

```yaml
# In mcp-servers/helm/values.yaml
mcpServers:
  oracle-sqlcl:
    enabled: true
    oracleSecret: oracle-db-user-sales-reader  # Read-only access
```

This automatically maps:
- `ORACLE_USER` → username
- `ORACLE_PWD` → password
- `ORACLE_HOST` → host
- `ORACLE_PORT` → port
- `ORACLE_SERVICE` → serviceName

---

## 🎉 Success!

You now have a production-ready Oracle 23ai deployment with:
- Automatic user management with secure passwords
- Optional TPC-DS benchmark data
- Kubernetes-native secret management
- Ready for AI/MCP server integration

For questions or issues, check the troubleshooting section above or review the Helm chart templates for detailed implementation.
