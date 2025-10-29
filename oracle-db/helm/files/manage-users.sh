#!/bin/bash
# manage-users.sh
# Oracle Database User Management
#
# Manages Oracle database users from Kubernetes secrets:
# - Waits for Oracle readiness
# - Creates users with appropriate permissions
# - Supports read-write (rw) and read-only (ro) modes
#
# Required environment variables:
#   ADMIN_USERNAME - Admin user username
#   ADMIN_PASSWORD - Admin user password

set -e

# Configuration
readonly ORACLE_SERVICE="${ORACLE_SERVICE:-freepdb1}"
readonly ORACLE_HOST="${ORACLE_HOST:-localhost}"
readonly ORACLE_PORT="${ORACLE_PORT:-1521}"
readonly SECRETS_DIR="${SECRETS_DIR:-/user-secrets}"
readonly MAX_WAIT="${MAX_WAIT:-600}"

# ============================================================================
# Wait for Oracle database to be ready
# ============================================================================
wait_for_oracle() {
  echo "[INFO] Waiting for Oracle database to be ready..."
  echo "[INFO] Checking for ${ORACLE_SERVICE} service availability..."

  local elapsed=0
  local retry_interval=15

  while [[ $elapsed -lt $MAX_WAIT ]]; do
    if echo "SELECT 'READY' FROM DUAL;" | sqlplus -s ${ADMIN_USERNAME}/"${ADMIN_PASSWORD}"@${ORACLE_HOST}:${ORACLE_PORT}/${ORACLE_SERVICE} 2>&1 | grep -q "READY"; then
      echo "[INFO] Service ${ORACLE_SERVICE} is accessible and ready"
      return 0
    fi

    echo "[INFO] Waiting for ${ORACLE_SERVICE} service... (${elapsed}s elapsed)"
    sleep $retry_interval
    elapsed=$((elapsed + retry_interval))
  done

  echo "[ERROR] Oracle database not ready after ${MAX_WAIT}s"
  return 1
}

# ============================================================================
# Attempt to create Oracle user (single attempt)
# ============================================================================
attempt_create_user() {
  local username="$1"
  local password="$2"
  local schema="$3"
  local mode="$4"

  # Build SQL for mode-specific privileges
  local mode_privileges=""
  if [[ "${mode}" == "rw" ]]; then
    mode_privileges="
-- Read-Write mode: Full schema privileges
GRANT RESOURCE TO ${username};
GRANT CREATE TABLE TO ${username};
GRANT CREATE VIEW TO ${username};
GRANT CREATE SEQUENCE TO ${username};
GRANT CREATE PROCEDURE TO ${username};
GRANT CREATE TRIGGER TO ${username};
GRANT CREATE TYPE TO ${username};
GRANT CREATE SYNONYM TO ${username};
"
  elif [[ "${mode}" == "ro" ]]; then
    mode_privileges="
-- Read-Only mode: Limited privileges
-- SELECT grants will be added by schema owners
GRANT CREATE SESSION TO ${username};
"
  fi

  # Execute SQL
  sqlplus -s ${ADMIN_USERNAME}/"${ADMIN_PASSWORD}"@${ORACLE_HOST}:${ORACLE_PORT}/${ORACLE_SERVICE} <<EOF
WHENEVER SQLERROR EXIT SQL.SQLCODE

-- Create user (if doesn't exist)
DECLARE
  user_exists NUMBER;
BEGIN
  SELECT COUNT(*) INTO user_exists FROM dba_users WHERE username = UPPER('${username}');

  IF user_exists = 0 THEN
    EXECUTE IMMEDIATE 'CREATE USER ${username} IDENTIFIED BY "${password}"';
  ELSE
    -- Update password if user exists
    EXECUTE IMMEDIATE 'ALTER USER ${username} IDENTIFIED BY "${password}"';
  END IF;
END;
/

-- Grant basic connect privileges
GRANT CONNECT TO ${username};
GRANT CREATE SESSION TO ${username};

-- Set default tablespace
ALTER USER ${username} DEFAULT TABLESPACE USERS;
ALTER USER ${username} QUOTA UNLIMITED ON USERS;

${mode_privileges}

EXIT;
EOF

  if [[ $? -eq 0 ]]; then
    return 0
  else
    return 1
  fi
}

# ============================================================================
# Create Oracle user with retries
# ============================================================================
create_oracle_user() {
  local username="$1"
  local password="$2"
  local schema="$3"
  local mode="$4"
  local max_retries=3
  local retry_delay=10

  echo "[INFO] Creating user: ${username}"
  echo "[INFO]   Schema: ${schema}"
  echo "[INFO]   Mode: ${mode}"

  for attempt in $(seq 1 $max_retries); do
    if attempt_create_user "${username}" "${password}" "${schema}" "${mode}"; then
      echo "[INFO] User ${username} created successfully"
      return 0
    fi

    if [[ $attempt -lt $max_retries ]]; then
      echo "[WARN] User creation failed, retrying in ${retry_delay}s... (attempt $attempt/$max_retries)"
      sleep $retry_delay
    fi
  done

  echo "[ERROR] Failed to create user ${username} after ${max_retries} attempts"
  return 1
}

# ============================================================================
# Grant permissions to alias user on target schema
# ============================================================================
grant_schema_permissions() {
  local username="$1"
  local target_schema="$2"
  local mode="$3"

  echo "[INFO] Granting ${mode} permissions on ${target_schema} schema to ${username}"

  if [[ "${mode}" == "rw" ]]; then
    # Read-write: Grant full DML on all tables
    sqlplus -s "${ADMIN_USERNAME}/${ADMIN_PASSWORD}@${ORACLE_HOST}:${ORACLE_PORT}/${ORACLE_SERVICE}" <<EOF
WHENEVER SQLERROR EXIT SQL.SQLCODE

-- Grant permissions on all existing tables
BEGIN
  FOR t IN (SELECT table_name FROM dba_tables WHERE owner = UPPER('${target_schema}')) LOOP
    EXECUTE IMMEDIATE 'GRANT SELECT, INSERT, UPDATE, DELETE ON ${target_schema}.' || t.table_name || ' TO ${username}';
  END LOOP;
END;
/

EXIT;
EOF
  elif [[ "${mode}" == "ro" ]]; then
    # Read-only: Grant SELECT on all tables
    sqlplus -s "${ADMIN_USERNAME}/${ADMIN_PASSWORD}@${ORACLE_HOST}:${ORACLE_PORT}/${ORACLE_SERVICE}" <<EOF
WHENEVER SQLERROR EXIT SQL.SQLCODE

-- Grant SELECT on all existing tables
BEGIN
  FOR t IN (SELECT table_name FROM dba_tables WHERE owner = UPPER('${target_schema}')) LOOP
    EXECUTE IMMEDIATE 'GRANT SELECT ON ${target_schema}.' || t.table_name || ' TO ${username}';
  END LOOP;
END;
/

EXIT;
EOF
  fi

  return $?
}

# ============================================================================
# Process all users from mounted secrets
# ============================================================================
process_users() {
  echo "[INFO] Processing user accounts..."
  echo "=================================="

  # First pass: Create schema owners (username == schema)
  echo ""
  echo "[INFO] Phase 1: Creating schema owners..."
  echo "========================================="

  for secret_dir in "${SECRETS_DIR}"/*; do
    if [[ ! -d "${secret_dir}" ]]; then
      continue
    fi

    local username=$(basename "${secret_dir}")

    # Skip admin user - it already exists
    if [[ "${username}" == "${ADMIN_USERNAME}" ]]; then
      echo "[INFO] Skipping admin user ${ADMIN_USERNAME} (already exists)"
      continue
    fi

    # Read user configuration
    if [[ ! -f "${secret_dir}/password" ]] || [[ ! -f "${secret_dir}/schema" ]] || [[ ! -f "${secret_dir}/mode" ]]; then
      echo "[WARN] Incomplete secret for user ${username}, skipping"
      continue
    fi

    local password=$(cat "${secret_dir}/password")
    local schema=$(cat "${secret_dir}/schema")
    local mode=$(cat "${secret_dir}/mode")

    # Only process schema owners in this pass
    if [[ "${username}" == "${schema}" ]]; then
      echo ""
      echo "[INFO] Processing schema owner: ${username}"
      if ! create_oracle_user "${username}" "${password}" "${schema}" "${mode}"; then
        echo "[ERROR] Failed to create schema owner ${username}"
        return 1
      fi
    fi
  done

  # Second pass: Create alias users (username != schema)
  echo ""
  echo "[INFO] Phase 2: Creating alias users..."
  echo "========================================"

  for secret_dir in "${SECRETS_DIR}"/*; do
    if [[ ! -d "${secret_dir}" ]]; then
      continue
    fi

    local username=$(basename "${secret_dir}")

    # Skip admin user
    if [[ "${username}" == "${ADMIN_USERNAME}" ]]; then
      continue
    fi

    # Read user configuration
    if [[ ! -f "${secret_dir}/password" ]] || [[ ! -f "${secret_dir}/schema" ]] || [[ ! -f "${secret_dir}/mode" ]]; then
      continue
    fi

    local password=$(cat "${secret_dir}/password")
    local schema=$(cat "${secret_dir}/schema")
    local mode=$(cat "${secret_dir}/mode")

    # Only process alias users in this pass
    if [[ "${username}" != "${schema}" ]]; then
      echo ""
      echo "[INFO] Processing alias user: ${username} -> ${schema} schema"
      if ! create_oracle_user "${username}" "${password}" "${schema}" "${mode}"; then
        echo "[ERROR] Failed to create alias user ${username}"
        return 1
      fi

      # Grant permissions on target schema
      if ! grant_schema_permissions "${username}" "${schema}" "${mode}"; then
        echo "[WARN] Failed to grant permissions for ${username} on ${schema} schema"
        echo "[WARN] Permissions will be granted after tables are created"
      fi
    fi
  done

  echo ""
  echo "[INFO] All users created successfully"
}

# ============================================================================
# Keep sidecar alive for monitoring
# ============================================================================
keep_alive() {
  echo "[INFO] User management complete - keeping sidecar alive for monitoring"

  # Create readiness marker
  touch /tmp/users-ready

  # Monitor loop
  while true; do
    sleep 300
    echo "[INFO] User management sidecar health check ($(date))"
  done
}

# ============================================================================
# Main execution
# ============================================================================
main() {
  echo "Oracle User Management Starting"
  echo "=================================="

  # Validation
  if [[ -z "${ADMIN_PASSWORD}" ]]; then
    echo "[ERROR] ADMIN_PASSWORD not set"
    exit 1
  fi

  # Execute workflow
  wait_for_oracle || exit 1
  echo ""
  process_users || exit 1
  echo ""
  keep_alive
}

# Run main
main
