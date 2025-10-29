#!/bin/bash
set -e

echo "Starting Oracle SQLcl MCP Server..."
echo "ORACLE_HOME: $ORACLE_HOME"
echo "JAVA_HOME: $JAVA_HOME"
echo "PATH: $PATH"

# Validate required Oracle environment variables
if [ -z "$ORACLE_USER" ] || [ -z "$ORACLE_PWD" ] || [ -z "$ORACLE_HOST" ] || [ -z "$ORACLE_PORT" ] || [ -z "$ORACLE_SERVICE" ]; then
  echo "ERROR: Missing required Oracle connection environment variables"
  echo "Required: ORACLE_USER, ORACLE_PWD, ORACLE_HOST, ORACLE_PORT, ORACLE_SERVICE"
  echo "Current values:"
  echo "  ORACLE_USER: ${ORACLE_USER:-<not set>}"
  echo "  ORACLE_PWD: ${ORACLE_PWD:+<set>}"
  echo "  ORACLE_HOST: ${ORACLE_HOST:-<not set>}"
  echo "  ORACLE_PORT: ${ORACLE_PORT:-<not set>}"
  echo "  ORACLE_SERVICE: ${ORACLE_SERVICE:-<not set>}"
  exit 1
fi

echo "Starting MCP Server for Toolhive proxy access..."

# Avoid JVM option injection issues
unset JAVA_TOOL_OPTIONS || true
unset _JAVA_OPTIONS || true

# Ensure writable Java temp directory to avoid Jansi lock error
mkdir -p /sqlcl-home/tmp || true
# Ensure a stable home directory for SQLcl user data (saved connections)
export HOME=/sqlcl-home
export JAVA_TOOL_OPTIONS="-Djava.io.tmpdir=/sqlcl-home/tmp -Duser.home=/sqlcl-home"
echo "JAVA_TOOL_OPTIONS: $JAVA_TOOL_OPTIONS"

# Avoid thick driver warning and site/user profile side effects
unset ORACLE_HOME || true
echo "ORACLE_HOME after unset: ${ORACLE_HOME:-<unset>}"
mkdir -p /sqlcl-home/empty || true
export SQLPATH=/sqlcl-home/empty
cd /sqlcl-home || true

# Build connection string and test connection
ORACLE_CONNECTION_STRING="${ORACLE_HOST}:${ORACLE_PORT}/${ORACLE_SERVICE}"
echo "Oracle Connection: ${ORACLE_USER}@${ORACLE_CONNECTION_STRING}"

# Wait for database connection to be available (retry for 30 minutes)
echo "Waiting for database connection to be available..."
MAX_RETRIES=360  # 30 minutes with 5-second intervals
RETRY_COUNT=0
CONNECTION_ALIAS=${ORACLE_CONN_NAME:-oracle_connection}

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
  echo "Testing connection to Oracle (attempt $((RETRY_COUNT + 1))/$MAX_RETRIES)..."
  if /opt/oracle/sqlcl/bin/sql -S -L ${ORACLE_USER}/${ORACLE_PWD}@${ORACLE_CONNECTION_STRING} <<< "exit" 2>&1; then
    echo "Successfully connected to Oracle database!"

    # Connection test successful, now try to create saved connection
    echo "Creating saved connection: $CONNECTION_ALIAS"
    if echo "connect -savepwd -save $CONNECTION_ALIAS ${ORACLE_USER}/${ORACLE_PWD}@${ORACLE_CONNECTION_STRING}" | /opt/oracle/sqlcl/bin/sql /NOLOG 2>&1; then
      echo "Successfully created saved connection: $CONNECTION_ALIAS"
      break
    else
      echo "WARNING: Failed to create saved connection. Retrying in 5 seconds..."
    fi
  else
    echo "Connection test failed. Retrying in 5 seconds..."
  fi

  RETRY_COUNT=$((RETRY_COUNT + 1))
  if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
    sleep 5
  fi
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
  echo "ERROR: Failed to connect to Oracle and create saved connection after 30 minutes"
  exit 1
fi

# Start SQLcl MCP
exec /opt/oracle/sqlcl/bin/sql -mcp
