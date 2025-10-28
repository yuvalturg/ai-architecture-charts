#!/bin/bash
set -e

echo "Starting Oracle SQLcl MCP Server..."
echo "ORACLE_HOME: $ORACLE_HOME"
echo "JAVA_HOME: $JAVA_HOME"
echo "PATH: $PATH"
echo "Oracle Connection: $ORACLE_CONNECTION_STRING"

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

# Test and create saved SQLcl connection if env vars provided
if [ -n "$ORACLE_USER" ] && [ -n "$ORACLE_PASSWORD" ] && [ -n "$ORACLE_CONNECTION_STRING" ]; then
  # Wait for database connection to be available (retry for 30 minutes)
  echo "Waiting for database connection to be available..."
  MAX_RETRIES=360  # 30 minutes with 5-second intervals
  RETRY_COUNT=0
  CONNECTION_ALIAS=${ORACLE_CONN_NAME:-oracle_connection}

  while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    echo "Testing connection to Oracle (attempt $((RETRY_COUNT + 1))/$MAX_RETRIES)..."
    if /opt/oracle/sqlcl/bin/sql -S -L ${ORACLE_USER}/${ORACLE_PASSWORD}@${ORACLE_CONNECTION_STRING} <<< "exit" 2>&1; then
      echo "Successfully connected to Oracle database!"

      # Connection test successful, now try to create saved connection
      echo "Creating saved connection: $CONNECTION_ALIAS"
      if echo "connect -savepwd -save $CONNECTION_ALIAS ${ORACLE_USER}/${ORACLE_PASSWORD}@${ORACLE_CONNECTION_STRING}" | /opt/oracle/sqlcl/bin/sql /NOLOG 2>&1; then
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
else
  echo "Skipping connection test and saved connection creation; missing ORACLE_USER/ORACLE_PASSWORD/ORACLE_CONNECTION_STRING environment variables"
fi

# Start SQLcl MCP
exec /opt/oracle/sqlcl/bin/sql -mcp
