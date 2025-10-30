#!/bin/bash
# create-users.sh
# Oracle Database User Creation
#
# Creates Oracle database users from Kubernetes secrets:
# - Creates users with appropriate permissions
# - Supports read-write (rw) and read-only (ro) modes
#
# Required environment variables:
#   ORACLE_USER - Admin user username (system)
#   ORACLE_PWD - Admin user password

set -e

# Configuration
readonly ORACLE_SERVICE="${ORACLE_SERVICE:-freepdb1}"
readonly ORACLE_HOST="${ORACLE_HOST:-localhost}"
readonly ORACLE_PORT="${ORACLE_PORT:-1521}"
readonly SECRETS_DIR="${SECRETS_DIR:-/user-secrets}"
readonly MAX_WAIT="${MAX_WAIT:-600}"

# ============================================================================
# Create Oracle user
# ============================================================================
create_oracle_user() {
  local username="$1"
  local password="$2"
  local schema="$3"
  local mode="$4"

  echo "[INFO] Creating user: ${username}"
  echo "[INFO]   Schema: ${schema}"
  echo "[INFO]   Mode: ${mode}"

  # Build SQL for mode-specific privileges
  local mode_privileges=""
  if [[ "${mode}" == "rw" ]]; then
    mode_privileges="
-- Read-Write mode: Full schema privileges
-- CONNECT role: CREATE SESSION
-- RESOURCE role: CREATE TABLE, CREATE SEQUENCE, CREATE TRIGGER, CREATE PROCEDURE, CREATE TYPE
GRANT CONNECT, RESOURCE TO ${username};
GRANT CREATE VIEW, CREATE SYNONYM TO ${username};
ALTER USER ${username} QUOTA UNLIMITED ON USERS;
"
  elif [[ "${mode}" == "ro" ]]; then
    mode_privileges="
-- Read-Only mode: Minimal privileges only
-- SELECT grants will be added after tables are created by TPC-DS job
GRANT CREATE SESSION TO ${username};
"
  fi

  # Execute SQL
  sqlplus -s ${ORACLE_USER}/"${ORACLE_PWD}"@${ORACLE_HOST}:${ORACLE_PORT}/${ORACLE_SERVICE} <<EOF
SET SERVEROUTPUT OFF
WHENEVER SQLERROR CONTINUE

-- Create user (ignore if already exists)
CREATE USER ${username} IDENTIFIED BY "${password}";

WHENEVER SQLERROR EXIT FAILURE

-- Update password and tablespace (works for new and existing users)
ALTER USER ${username} IDENTIFIED BY "${password}" DEFAULT TABLESPACE USERS;

-- Apply mode-specific privileges
${mode_privileges}

EXIT;
EOF

  if [[ $? -eq 0 ]]; then
    echo "[INFO] User ${username} created successfully"
    return 0
  else
    echo "[ERROR] Failed to create user ${username}"
    return 1
  fi
}

# ============================================================================
# Create schema owners (Phase 1)
# ============================================================================
create_schema_owners() {
  echo ""
  echo "[INFO] Phase 1: Creating schema owners..."
  echo "========================================="

  for secret_dir in "${SECRETS_DIR}"/*; do
    if [[ ! -d "${secret_dir}" ]]; then
      continue
    fi

    local username=$(basename "${secret_dir}")

    # Skip admin user - it already exists
    if [[ "${username}" == "${ORACLE_USER}" ]]; then
      echo "[INFO] Skipping admin user ${ORACLE_USER} (already exists)"
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

    # Only process schema owners (username == schema)
    if [[ "${username}" == "${schema}" ]]; then
      echo ""
      echo "[INFO] Processing schema owner: ${username}"
      if ! create_oracle_user "${username}" "${password}" "${schema}" "${mode}"; then
        echo "[ERROR] Failed to create schema owner ${username}"
        return 1
      fi
    fi
  done

  return 0
}

# ============================================================================
# Create alias users (Phase 2)
# ============================================================================
create_alias_users() {
  echo ""
  echo "[INFO] Phase 2: Creating alias users..."
  echo "========================================"

  for secret_dir in "${SECRETS_DIR}"/*; do
    if [[ ! -d "${secret_dir}" ]]; then
      continue
    fi

    local username=$(basename "${secret_dir}")

    # Skip admin user
    if [[ "${username}" == "${ORACLE_USER}" ]]; then
      continue
    fi

    # Read user configuration
    if [[ ! -f "${secret_dir}/password" ]] || [[ ! -f "${secret_dir}/schema" ]] || [[ ! -f "${secret_dir}/mode" ]]; then
      continue
    fi

    local password=$(cat "${secret_dir}/password")
    local schema=$(cat "${secret_dir}/schema")
    local mode=$(cat "${secret_dir}/mode")

    # Only process alias users (username != schema)
    if [[ "${username}" != "${schema}" ]]; then
      echo ""
      echo "[INFO] Processing alias user: ${username} -> ${schema} schema"
      if ! create_oracle_user "${username}" "${password}" "${schema}" "${mode}"; then
        echo "[ERROR] Failed to create alias user ${username}"
        return 1
      fi
    fi
  done

  return 0
}

# ============================================================================
# Process all users from mounted secrets
# ============================================================================
process_users() {
  echo "[INFO] Processing user accounts..."
  echo "=================================="

  create_schema_owners || return 1
  create_alias_users || return 1

  echo ""
  echo "[INFO] All users created successfully"
  return 0
}

# ============================================================================
# Main execution
# ============================================================================
main() {
  echo "Oracle User Creation Starting"
  echo "=============================="

  # Validation
  if [[ -z "${ORACLE_PWD}" ]]; then
    echo "[ERROR] ORACLE_PWD not set"
    exit 1
  fi

  if [[ -z "${ORACLE_USER}" ]]; then
    echo "[ERROR] ORACLE_USER not set"
    exit 1
  fi

  # Execute workflow
  echo ""
  process_users || exit 1
  echo ""
  echo "[INFO] User creation completed successfully"
}

# Run main
main
