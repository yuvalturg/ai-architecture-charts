"""Database connection and operations for Oracle."""

import os
from contextlib import contextmanager

import oracledb

# Force thin mode by clearing Oracle environment variables
for var in ["ORACLE_HOME", "TNS_ADMIN", "ORACLE_BASE"]:
    if var in os.environ:
        del os.environ[var]
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .config import config_manager

console = Console()


class DatabaseManager:
    """Manages Oracle database connections and operations."""

    def __init__(self):
        self.config = config_manager.load()

    def _get_schema_name(self, schema_override: Optional[str] = None) -> str:
        """Get effective schema name (override > config > current user)."""
        if schema_override:
            return schema_override.upper()
        elif self.config.schema_name:
            return self.config.schema_name.upper()
        else:
            # Use current user's schema (default behavior)
            return ""

    def _qualify_table_name(self, table_name: str, schema_name: str = "") -> str:
        """Qualify table name with schema if provided."""
        if schema_name:
            return f"{schema_name}.{table_name.upper()}"
        else:
            return table_name.upper()

    @contextmanager
    def get_connection(self) -> Generator[oracledb.Connection, None, None]:
        """Get database connection context manager."""
        password = config_manager.get_password()

        try:
            connection = oracledb.connect(
                user=self.config.database.username,
                password=password,
                dsn=self.config.database.dsn,
            )
            # Enable autocommit to prevent transaction rollback on container termination
            connection.autocommit = True
            yield connection
        except oracledb.Error as e:
            click.echo(f"Database connection error: {e}", err=True)
            raise
        finally:
            if "connection" in locals():
                connection.close()

    def test_connection(self) -> bool:
        """Test database connection."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1 FROM DUAL")
                    result = cursor.fetchone()
                    return result is not None
        except Exception:
            return False

    def _qualify_sql_for_schema(self, sql_content: str, target_schema: str) -> str:
        """Modify SQL statements to be schema-qualified for the target schema."""
        if not target_schema:
            return sql_content

        # Define TPC-DS table names that need to be qualified
        tpcds_tables = [
            "CALL_CENTER",
            "CATALOG_PAGE",
            "CATALOG_RETURNS",
            "CATALOG_SALES",
            "CUSTOMER",
            "CUSTOMER_ADDRESS",
            "CUSTOMER_DEMOGRAPHICS",
            "DATE_DIM",
            "HOUSEHOLD_DEMOGRAPHICS",
            "INCOME_BAND",
            "INVENTORY",
            "ITEM",
            "PROMOTION",
            "REASON",
            "SHIP_MODE",
            "STORE",
            "STORE_RETURNS",
            "STORE_SALES",
            "TIME_DIM",
            "WAREHOUSE",
            "WEB_PAGE",
            "WEB_RETURNS",
            "WEB_SALES",
            "WEB_SITE",
            "DBGEN_VERSION",
        ]

        import re

        modified_sql = sql_content

        # Replace CREATE TABLE statements to target the specified schema
        for table in tpcds_tables:
            # Pattern for CREATE TABLE statements (case insensitive)
            pattern = rf"\bcreate\s+table\s+{table}\b"
            replacement = f"create table {target_schema}.{table}"
            modified_sql = re.sub(
                pattern, replacement, modified_sql, flags=re.IGNORECASE
            )

            # Also handle DROP TABLE statements in the cleanup section
            pattern = rf"\bdrop\s+table\s+{table}\b"
            replacement = f"drop table {target_schema}.{table}"
            modified_sql = re.sub(
                pattern, replacement, modified_sql, flags=re.IGNORECASE
            )

        # Handle the dynamic cleanup section that queries user_tables
        # Replace user_tables with all_tables and add owner condition
        if "user_tables" in modified_sql:
            modified_sql = modified_sql.replace(
                "user_tables", f"all_tables WHERE owner = '{target_schema.upper()}'"
            )
            # Fix the WHERE clause to avoid double WHERE
            modified_sql = re.sub(
                r"all_tables WHERE owner = '[^']+' WHERE",
                f"all_tables WHERE owner = '{target_schema.upper()}' AND",
                modified_sql,
            )

        return modified_sql

    def execute_sql_file(
        self, sql_file: Path, target_schema: Optional[str] = None
    ) -> bool:
        """Execute SQL statements from a file, optionally targeting a specific schema."""
        if not sql_file.exists():
            click.echo(f"SQL file not found: {sql_file}", err=True)
            return False

        try:
            with open(sql_file, "r") as f:
                sql_content = f.read()

            # Modify SQL for target schema if specified
            if target_schema:
                sql_content = self._qualify_sql_for_schema(sql_content, target_schema)
                console.print(
                    f"📝 Modified SQL statements for target schema: {target_schema}",
                    style="cyan",
                )

            # Handle Oracle PL/SQL blocks which end with /
            # Split by / when it's on its own line, otherwise split by ;
            statements = []
            current_stmt = ""
            lines = sql_content.split("\n")

            for line in lines:
                stripped_line = line.strip()

                # Skip comment lines
                if stripped_line.startswith("--") or not stripped_line:
                    continue

                if stripped_line == "/":
                    # End of PL/SQL block
                    if current_stmt.strip():
                        statements.append(current_stmt.strip())
                        current_stmt = ""
                elif stripped_line.endswith(";") and not any(
                    keyword in current_stmt.upper() for keyword in ["BEGIN", "DECLARE"]
                ):
                    # Regular SQL statement - remove the semicolon and add to statements
                    current_stmt += stripped_line[:-1]  # Remove semicolon
                    if current_stmt.strip():
                        statements.append(current_stmt.strip())
                    current_stmt = ""
                else:
                    # Continue building statement
                    if current_stmt:
                        current_stmt += "\n" + stripped_line
                    else:
                        current_stmt = stripped_line

            # Add any remaining statement
            if current_stmt.strip():
                statements.append(current_stmt.strip())

            # Filter out empty statements and comments
            statements = [
                stmt
                for stmt in statements
                if stmt.strip() and not stmt.strip().startswith("--")
            ]

            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    with Progress(
                        SpinnerColumn(),
                        TextColumn("[progress.description]{task.description}"),
                        console=console,
                    ) as progress:
                        task = progress.add_task(
                            f"Executing {sql_file.name}...", total=len(statements)
                        )

                        for i, stmt in enumerate(statements):
                            if stmt.strip():
                                try:
                                    # Debug: print first few statements
                                    if i < 3:
                                        console.print(
                                            f"Executing statement {i + 1}: {stmt[:100]}...",
                                            style="cyan",
                                        )
                                    cursor.execute(stmt)
                                    progress.advance(task)
                                except oracledb.Error as e:
                                    # Log the error but continue with next statement
                                    console.print(
                                        f"Error in statement {i + 1}: {str(e)[:150]}",
                                        style="red",
                                    )
                                    if i < 3:
                                        console.print(
                                            f"Failed statement: {stmt[:200]}",
                                            style="red",
                                        )
                                    progress.advance(task)

                        conn.commit()

            console.print(f"✅ Successfully executed {sql_file.name}", style="green")
            return True

        except Exception as e:
            click.echo(f"Error executing SQL file {sql_file}: {e}", err=True)
            return False

    def _check_schema_user_exists(self, schema_name: str) -> bool:
        """Check if a schema/user exists in the database."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT COUNT(*) FROM all_users WHERE username = :schema_name",
                        {"schema_name": schema_name.upper()},
                    )
                    return cursor.fetchone()[0] > 0
        except Exception:
            return False

    def _create_schema_user(self, schema_name: str, user_password: str = None) -> bool:
        """Create a new database user/schema with appropriate privileges."""
        try:
            # Use provided password or get from environment
            if not user_password:
                user_password = os.getenv("TPCDS_DB_PASSWORD")
                if not user_password:
                    user_password = f"{schema_name.lower()}_pass123"

            console.print(f"📋 Creating database user: {schema_name}", style="cyan")

            # Use SYSDBA connection for user creation
            try:
                # Try to connect as SYSDBA first for user creation
                connection = oracledb.connect(
                    dsn=self.config.database.dsn, mode=oracledb.AUTH_MODE_SYSDBA
                )
                connection.autocommit = True

                with connection.cursor() as cursor:
                    # Switch to FREEPDB1
                    cursor.execute("ALTER SESSION SET CONTAINER = FREEPDB1")

                    # Check if user exists
                    cursor.execute(
                        "SELECT COUNT(*) FROM dba_users WHERE username = :username",
                        {"username": schema_name.upper()},
                    )
                    user_count = cursor.fetchone()[0]

                    if user_count == 0:
                        # Create the user with secure password handling
                        cursor.execute(
                            f'CREATE USER {schema_name} IDENTIFIED BY "{user_password}"'
                        )
                        console.print(
                            f"✅ User {schema_name} created successfully", style="green"
                        )
                    else:
                        console.print(
                            f"⚠️  User {schema_name} already exists", style="yellow"
                        )

                    # Grant basic privileges
                    privileges = [
                        "CREATE SESSION",
                        "CREATE TABLE",
                        "CREATE SEQUENCE",
                        "CREATE VIEW",
                        "CREATE PROCEDURE",
                        "CREATE TRIGGER",
                        "CREATE SYNONYM",
                    ]

                    for privilege in privileges:
                        try:
                            cursor.execute(f"GRANT {privilege} TO {schema_name}")
                        except oracledb.Error:
                            pass  # May already be granted

                    # Grant unlimited tablespace quota
                    try:
                        cursor.execute(f"GRANT UNLIMITED TABLESPACE TO {schema_name}")
                    except oracledb.Error:
                        pass  # May already be granted

                    console.print(
                        f"✅ Privileges granted to user {schema_name}", style="green"
                    )
                    connection.close()
                    return True

            except oracledb.Error:
                # Fallback to regular connection if SYSDBA fails
                console.print(
                    "🔄 SYSDBA access not available, trying alternative approach",
                    style="yellow",
                )
                return self._create_schema_user_fallback(schema_name, user_password)

        except Exception as e:
            console.print(f"❌ Error creating user {schema_name}: {e}", style="red")
            return False

    def _create_schema_user_fallback(
        self, schema_name: str, user_password: str
    ) -> bool:
        """Fallback method for user creation when SYSDBA is not available."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    console.print(
                        f"📋 Creating database user via fallback method: {schema_name}",
                        style="cyan",
                    )

                    # Create the user
                    cursor.execute(
                        f'CREATE USER {schema_name} IDENTIFIED BY "{user_password}"'
                    )

                    # Grant basic privileges
                    privileges = [
                        "CREATE SESSION",
                        "CREATE TABLE",
                        "UNLIMITED TABLESPACE",
                    ]

                    for privilege in privileges:
                        cursor.execute(f"GRANT {privilege} TO {schema_name}")

                    conn.commit()

                    console.print(
                        f"✅ Created database user {schema_name}", style="green"
                    )
                    console.print(
                        f"💡 Note: User {schema_name} has been granted necessary privileges for TPC-DS operations",
                        style="blue",
                    )

                    return True

        except oracledb.Error as e:
            if "ORA-01031" in str(e):
                console.print(
                    f"❌ Insufficient privileges to create user {schema_name}",
                    style="red",
                )
                console.print(
                    f"💡 Please ask your DBA to run: CREATE USER {schema_name} IDENTIFIED BY password",
                    style="blue",
                )
                console.print(
                    f"💡 And grant privileges: GRANT CREATE SESSION, CREATE TABLE, UNLIMITED TABLESPACE TO {schema_name}",
                    style="blue",
                )
            elif "ORA-01920" in str(e):  # User name already exists
                console.print(f"⚠️  User {schema_name} already exists", style="yellow")
                return True
            else:
                console.print(f"❌ Error creating user {schema_name}: {e}", style="red")
            return False
        except Exception as e:
            console.print(f"❌ Error creating user {schema_name}: {e}", style="red")
            return False

    def _check_create_privileges(self, target_schema: str) -> bool:
        """Check if current user can create tables in target schema."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Test if we can create a table in the target schema
                    test_table = f"{target_schema}.TPCDS_PRIVILEGE_TEST"
                    cursor.execute(f"CREATE TABLE {test_table} (test_col NUMBER)")
                    cursor.execute(f"DROP TABLE {test_table}")
                    conn.commit()
                    return True
        except oracledb.Error:
            return False
        except Exception:
            return False

    def create_schema(
        self, schema_file: Optional[Path] = None, schema_override: Optional[str] = None
    ) -> bool:
        """Create TPC-DS schema with automatic user/privilege management."""
        schema_name = self._get_schema_name(schema_override)

        if schema_file is None:
            # Look for oracle_tpcds_schema.sql in current directory
            candidates = [
                Path("oracle_tpcds_schema.sql"),
                Path("tpcds.sql"),
                Path("scripts/side_files/tpcds.sql"),
            ]

            for candidate in candidates:
                if candidate.exists():
                    schema_file = candidate
                    break

            if schema_file is None:
                click.echo(
                    "Schema file (oracle_tpcds_schema.sql or tpcds.sql) not found. Please specify path with --schema-file",
                    err=True,
                )
                return False

        # Handle schema creation logic
        if schema_name:
            console.print(f"🎯 Target schema: {schema_name}", style="cyan")

            # Check if target schema user exists
            if not self._check_schema_user_exists(schema_name):
                console.print(
                    f"📋 Schema user {schema_name} does not exist, creating...",
                    style="yellow",
                )
                if not self._create_schema_user(schema_name):
                    console.print(
                        f"❌ Failed to create schema user {schema_name}", style="red"
                    )
                    console.print(
                        f"💡 Proceeding to check if current user has privileges to create tables in {schema_name}",
                        style="blue",
                    )

            # Check if we have privileges to create tables in target schema
            if not self._check_create_privileges(schema_name):
                console.print(
                    f"❌ Current user cannot create tables in schema {schema_name}",
                    style="red",
                )
                console.print(f"💡 Options:", style="blue")
                console.print(
                    f"   1. Ask DBA to grant CREATE ANY TABLE privilege to current user",
                    style="blue",
                )
                console.print(
                    f"   2. Ask DBA to create user {schema_name} with necessary privileges",
                    style="blue",
                )
                console.print(
                    f"   3. Use current user's schema by omitting --schema parameter",
                    style="blue",
                )
                return False

            console.print(
                f"Creating TPC-DS schema from {schema_file} in schema {schema_name}"
            )
        else:
            console.print(
                f"Creating TPC-DS schema from {schema_file} in current user's schema"
            )

        return self.execute_sql_file(schema_file, target_schema=schema_name)

    def drop_schema(
        self, confirm: bool = False, schema_override: Optional[str] = None
    ) -> bool:
        """Drop TPC-DS tables (with confirmation). Note: This does not drop the Oracle schema/user itself."""
        schema_name = self._get_schema_name(schema_override)

        if not confirm:
            schema_msg = f" from schema {schema_name}" if schema_name else ""
            if not click.confirm(
                f"This will drop all TPC-DS tables and data{schema_msg} (not the schema itself). Continue?"
            ):
                click.echo("Operation cancelled.")
                return False

        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    # First, discover what TPC-DS tables actually exist
                    if schema_name:
                        # Query tables in specified schema
                        cursor.execute(
                            """
                            SELECT table_name 
                            FROM all_tables 
                            WHERE owner = :schema_name 
                            AND table_name IN (
                                'CALL_CENTER', 'CATALOG_PAGE', 'CATALOG_RETURNS', 'CATALOG_SALES',
                                'CUSTOMER', 'CUSTOMER_ADDRESS', 'CUSTOMER_DEMOGRAPHICS', 'DATE_DIM',
                                'HOUSEHOLD_DEMOGRAPHICS', 'INCOME_BAND', 'INVENTORY', 'ITEM',
                                'PROMOTION', 'REASON', 'SHIP_MODE', 'STORE', 'STORE_RETURNS',
                                'STORE_SALES', 'TIME_DIM', 'WAREHOUSE', 'WEB_PAGE', 'WEB_RETURNS',
                                'WEB_SALES', 'WEB_SITE', 'DBGEN_VERSION'
                            )
                            ORDER BY table_name
                        """,
                            {"schema_name": schema_name.upper()},
                        )
                    else:
                        # Query tables in current user schema
                        cursor.execute(
                            """
                            SELECT table_name 
                            FROM user_tables 
                            WHERE table_name IN (
                                'CALL_CENTER', 'CATALOG_PAGE', 'CATALOG_RETURNS', 'CATALOG_SALES',
                                'CUSTOMER', 'CUSTOMER_ADDRESS', 'CUSTOMER_DEMOGRAPHICS', 'DATE_DIM',
                                'HOUSEHOLD_DEMOGRAPHICS', 'INCOME_BAND', 'INVENTORY', 'ITEM',
                                'PROMOTION', 'REASON', 'SHIP_MODE', 'STORE', 'STORE_RETURNS',
                                'STORE_SALES', 'TIME_DIM', 'WAREHOUSE', 'WEB_PAGE', 'WEB_RETURNS',
                                'WEB_SALES', 'WEB_SITE', 'DBGEN_VERSION'
                            )
                            ORDER BY table_name
                        """
                        )

                    existing_tables = [row[0] for row in cursor.fetchall()]

                    if not existing_tables:
                        schema_msg = f" in schema {schema_name}" if schema_name else ""
                        console.print(
                            f"No TPC-DS tables found to drop{schema_msg}.",
                            style="yellow",
                        )
                        return True

                    console.print(
                        f"Found {len(existing_tables)} TPC-DS tables to drop",
                        style="cyan",
                    )

                    # Now drop the tables in dependency order (reverse of creation order)
                    # Fact tables first, then dimension tables
                    drop_order = [
                        "STORE_RETURNS",
                        "CATALOG_RETURNS",
                        "WEB_RETURNS",
                        "STORE_SALES",
                        "CATALOG_SALES",
                        "WEB_SALES",
                        "INVENTORY",
                        "CUSTOMER",
                        "CUSTOMER_ADDRESS",
                        "CUSTOMER_DEMOGRAPHICS",
                        "HOUSEHOLD_DEMOGRAPHICS",
                        "INCOME_BAND",
                        "ITEM",
                        "PROMOTION",
                        "REASON",
                        "SHIP_MODE",
                        "STORE",
                        "WAREHOUSE",
                        "WEB_PAGE",
                        "WEB_SITE",
                        "CATALOG_PAGE",
                        "CALL_CENTER",
                        "DATE_DIM",
                        "TIME_DIM",
                        "DBGEN_VERSION",
                    ]

                    # Filter to only tables that actually exist and preserve order
                    tables_to_drop = [
                        table for table in drop_order if table in existing_tables
                    ]
                    # Add any remaining tables not in the predefined order
                    tables_to_drop.extend(
                        [
                            table
                            for table in existing_tables
                            if table not in tables_to_drop
                        ]
                    )

                    with Progress(
                        SpinnerColumn(),
                        TextColumn("[progress.description]{task.description}"),
                        console=console,
                    ) as progress:
                        task = progress.add_task(
                            "Dropping TPC-DS tables...", total=len(tables_to_drop)
                        )

                        dropped_count = 0
                        failed_tables = []

                        for table in tables_to_drop:
                            try:
                                qualified_name = self._qualify_table_name(
                                    table, schema_name
                                )

                                # For cross-schema operations, we need different approaches
                                cursor.execute("SELECT USER FROM DUAL")
                                current_user = cursor.fetchone()[0]
                                if schema_name and schema_name.upper() != current_user:
                                    # Trying to drop tables in another schema
                                    # First try direct drop (if we have permission)
                                    try:
                                        cursor.execute(
                                            f"DROP TABLE {qualified_name} CASCADE CONSTRAINTS"
                                        )
                                        dropped_count += 1
                                    except oracledb.Error as e:
                                        if "ORA-01031" in str(
                                            e
                                        ):  # Insufficient privileges
                                            # Try to connect as the schema owner or use different approach
                                            console.print(
                                                f"Warning: Insufficient privileges to drop {qualified_name}",
                                                style="yellow",
                                            )
                                            failed_tables.append(table)
                                        elif "ORA-00942" in str(
                                            e
                                        ):  # Table doesn't exist
                                            pass  # Already handled by discovery query
                                        else:
                                            console.print(
                                                f"Warning: Failed to drop {qualified_name}: {e}",
                                                style="yellow",
                                            )
                                            failed_tables.append(table)
                                else:
                                    # Dropping tables in current user's schema
                                    cursor.execute(
                                        f"DROP TABLE {qualified_name} CASCADE CONSTRAINTS"
                                    )
                                    dropped_count += 1

                                progress.advance(task)

                            except oracledb.Error as e:
                                if "ORA-00942" not in str(
                                    e
                                ):  # Ignore "table doesn't exist"
                                    console.print(
                                        f"Warning: Failed to drop {table}: {e}",
                                        style="yellow",
                                    )
                                    failed_tables.append(table)
                                progress.advance(task)

                        conn.commit()

                    # Report results
                    if dropped_count > 0:
                        console.print(
                            f"✅ Successfully dropped {dropped_count} tables",
                            style="green",
                        )

                    if failed_tables:
                        console.print(
                            f"⚠️  Failed to drop {len(failed_tables)} tables: {', '.join(failed_tables)}",
                            style="yellow",
                        )
                        console.print(
                            "💡 Tip: You may need DBA privileges to drop tables in other schemas",
                            style="blue",
                        )

                    return len(failed_tables) == 0

        except Exception as e:
            click.echo(f"Error dropping schema: {e}", err=True)
            return False

    def get_table_info(
        self, schema_override: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get information about TPC-DS tables with actual row counts."""
        schema_name = self._get_schema_name(schema_override)

        # List of TPC-DS tables to check
        tpcds_tables = [
            "CALL_CENTER",
            "CATALOG_PAGE",
            "CATALOG_RETURNS",
            "CATALOG_SALES",
            "CUSTOMER",
            "CUSTOMER_ADDRESS",
            "CUSTOMER_DEMOGRAPHICS",
            "DATE_DIM",
            "HOUSEHOLD_DEMOGRAPHICS",
            "INCOME_BAND",
            "INVENTORY",
            "ITEM",
            "PROMOTION",
            "REASON",
            "SHIP_MODE",
            "STORE",
            "STORE_RETURNS",
            "STORE_SALES",
            "TIME_DIM",
            "WAREHOUSE",
            "WEB_PAGE",
            "WEB_RETURNS",
            "WEB_SALES",
            "WEB_SITE",
        ]

        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    results = []

                    for table in tpcds_tables:
                        qualified_table = self._qualify_table_name(table, schema_name)

                        try:
                            # Get actual row count using COUNT(*)
                            cursor.execute(f"SELECT COUNT(*) FROM {qualified_table}")
                            actual_rows = cursor.fetchone()[0]

                            # Get basic table info for blocks and avg_row_len (may be 0 if stats not updated)
                            if schema_name:
                                cursor.execute(
                                    """
                                SELECT blocks, avg_row_len 
                                FROM all_tables 
                                WHERE owner = :schema_name AND table_name = :table_name
                                """,
                                    {"schema_name": schema_name, "table_name": table},
                                )
                            else:
                                cursor.execute(
                                    """
                                SELECT blocks, avg_row_len 
                                FROM user_tables 
                                WHERE table_name = :table_name
                                """,
                                    {"table_name": table},
                                )

                            stats_row = cursor.fetchone()
                            if stats_row:
                                blocks, avg_row_len = stats_row
                            else:
                                blocks, avg_row_len = 0, 0

                            results.append(
                                {
                                    "TABLE_NAME": table,
                                    "NUM_ROWS": actual_rows,
                                    "BLOCKS": blocks or 0,
                                    "AVG_ROW_LEN": avg_row_len or 0,
                                }
                            )

                        except oracledb.Error as e:
                            if "ORA-00942" in str(e):  # Table doesn't exist
                                continue  # Skip non-existent tables
                            else:
                                # Table exists but other error, include with 0 count
                                results.append(
                                    {
                                        "TABLE_NAME": table,
                                        "NUM_ROWS": 0,
                                        "BLOCKS": 0,
                                        "AVG_ROW_LEN": 0,
                                    }
                                )

                    # Sort results by table name
                    results.sort(key=lambda x: x["TABLE_NAME"])
                    return results

        except Exception as e:
            click.echo(f"Error getting table info: {e}", err=True)
            return []

    def create_user(
        self, username: str, password: str = None, tablespace: str = "UNLIMITED"
    ) -> bool:
        """Create a new Oracle user/schema with appropriate privileges."""
        try:
            # Use the existing _create_schema_user method
            if password is None:
                password = (
                    os.getenv("TPCDS_DB_PASSWORD") or f"{username.lower()}_pass123"
                )

            return self._create_schema_user(username, password)

        except Exception as e:
            console.print(f"❌ Error creating user {username}: {e}", style="red")
            return False

    def restrict_user_privileges(self, username: str) -> bool:
        """Restrict a user by removing dangerous system privileges.

        Note: Oracle table owners always have full DML privileges on their own tables.
        This function documents the limitation and removes what privileges it can.

        Args:
            username: Username/schema to restrict

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            console.print(
                f"🔒 Restricting privileges for user {username}...", style="cyan"
            )
            console.print(
                f"⚠️  Oracle limitation: Table owners cannot be made read-only to their own tables",
                style="yellow",
            )
            console.print(
                f"   For true read-only access, create a separate user with SELECT-only grants",
                style="yellow",
            )
            console.print(
                f"   Current approach: Revoke system privileges only", style="yellow"
            )

            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    # List of dangerous privileges to revoke
                    dangerous_privileges = [
                        "CREATE TABLE",
                        "CREATE INDEX",
                        "CREATE VIEW",
                        "CREATE PROCEDURE",
                        "CREATE FUNCTION",
                        "CREATE PACKAGE",
                        "CREATE TRIGGER",
                        "CREATE SEQUENCE",
                        "CREATE SYNONYM",
                        "CREATE TYPE",
                        "CREATE MATERIALIZED VIEW",
                    ]

                    # Revoke dangerous system privileges
                    revoked_count = 0
                    for privilege in dangerous_privileges:
                        try:
                            cursor.execute(
                                f"REVOKE {privilege} FROM {username.upper()}"
                            )
                            revoked_count += 1
                        except oracledb.Error:
                            # Privilege might not have been granted, continue
                            pass

                    # Ensure user can still connect
                    try:
                        cursor.execute(f"GRANT CREATE SESSION TO {username.upper()}")
                    except oracledb.Error:
                        pass  # Might already be granted

                    console.print(
                        f"✅ Revoked {revoked_count} system privileges from {username}",
                        style="green",
                    )
                    console.print(
                        f"⚠️  Warning: User can still modify their own tables (Oracle limitation)",
                        style="yellow",
                    )
                    console.print(
                        f"   For AI/MCP servers, consider using SYSTEM schema with SELECT grants",
                        style="dim",
                    )
                    return True

        except Exception as e:
            console.print(f"❌ Error modifying user {username}: {e}", style="red")
            return False

    def copy_schema(
        self,
        source_schema: str,
        target_schema: str,
        table_list: List[str] = None,
        include_data: bool = True,
    ) -> bool:
        """Copy tables from one schema to another.

        Args:
            source_schema: Source schema name to copy from
            target_schema: Target schema name to copy to
            table_list: Optional list of specific tables to copy (defaults to all TPC-DS tables)
            include_data: Whether to copy data or just structure (default: True)

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Default to ALL TPC-DS tables if no specific list provided
            if table_list is None:
                table_list = [
                    "DBGEN_VERSION",
                    "CUSTOMER_ADDRESS",
                    "CUSTOMER_DEMOGRAPHICS",
                    "DATE_DIM",
                    "WAREHOUSE",
                    "SHIP_MODE",
                    "TIME_DIM",
                    "REASON",
                    "INCOME_BAND",
                    "ITEM",
                    "STORE",
                    "CALL_CENTER",
                    "CUSTOMER",
                    "WEB_SITE",
                    "STORE_RETURNS",
                    "HOUSEHOLD_DEMOGRAPHICS",
                    "WEB_PAGE",
                    "PROMOTION",
                    "CATALOG_PAGE",
                    "INVENTORY",
                    "CATALOG_RETURNS",
                    "WEB_RETURNS",
                    "WEB_SALES",
                    "CATALOG_SALES",
                    "STORE_SALES",
                ]

            console.print(
                f"📋 Copying {len(table_list)} tables from {source_schema} to {target_schema}",
                style="cyan",
            )

            # Ensure target user exists
            if not self._check_schema_user_exists(target_schema):
                console.print(
                    f"📋 Target schema {target_schema} doesn't exist, creating...",
                    style="yellow",
                )
                if not self.create_user(target_schema):
                    console.print(
                        f"❌ Failed to create target schema {target_schema}",
                        style="red",
                    )
                    return False

            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    successful_copies = 0
                    failed_copies = []

                    with Progress(
                        SpinnerColumn(),
                        TextColumn("[progress.description]{task.description}"),
                        console=console,
                    ) as progress:
                        task = progress.add_task(
                            f"Copying tables to {target_schema}...",
                            total=len(table_list),
                        )

                        for table in table_list:
                            try:
                                source_table = (
                                    f"{source_schema.upper()}.{table.upper()}"
                                )
                                target_table = (
                                    f"{target_schema.upper()}.{table.upper()}"
                                )

                                # Check if source table exists
                                check_sql = f"SELECT COUNT(*) FROM all_tables WHERE owner = '{source_schema.upper()}' AND table_name = '{table.upper()}'"
                                cursor.execute(check_sql)

                                if cursor.fetchone()[0] == 0:
                                    console.print(
                                        f"⚠️  Source table {source_table} doesn't exist, skipping",
                                        style="yellow",
                                    )
                                    progress.advance(task)
                                    continue

                                # Drop target table if it exists
                                try:
                                    cursor.execute(
                                        f"DROP TABLE {target_table} CASCADE CONSTRAINTS"
                                    )
                                    console.print(
                                        f"🗑️  Dropped existing {target_table}",
                                        style="yellow",
                                    )
                                except oracledb.Error:
                                    pass  # Table doesn't exist, which is fine

                                if include_data:
                                    # Copy table structure and data
                                    console.print(
                                        f"📊 Copying {table} with data...", style="cyan"
                                    )
                                    sql = f"CREATE TABLE {target_schema.upper()}.{table.upper()} AS SELECT * FROM {source_schema.upper()}.{table.upper()}"
                                    cursor.execute(sql)
                                else:
                                    # Copy table structure only
                                    console.print(
                                        f"🏗️  Copying {table} structure only...",
                                        style="cyan",
                                    )
                                    sql = (
                                        f"CREATE TABLE {target_schema.upper()}.{table.upper()} "
                                        f"AS SELECT * FROM {source_schema.upper()}.{table.upper()} WHERE 1=0"
                                    )
                                    cursor.execute(sql)

                                successful_copies += 1
                                console.print(
                                    f"✅ Successfully copied {table}", style="green"
                                )

                            except oracledb.Error as e:
                                error_msg = str(e)
                                if "ORA-01031" in error_msg:
                                    console.print(
                                        f"❌ Insufficient privileges to copy {table}",
                                        style="red",
                                    )
                                elif "ORA-00942" in error_msg:
                                    console.print(
                                        f"❌ Source table {table} not found",
                                        style="red",
                                    )
                                else:
                                    console.print(
                                        f"❌ Error copying {table}: {error_msg[:100]}",
                                        style="red",
                                    )
                                failed_copies.append(table)

                            progress.advance(task)

                        conn.commit()

                    # Report results
                    console.print(f"📈 Copy Summary:", style="bold blue")
                    console.print(
                        f"✅ Successfully copied: {successful_copies} tables",
                        style="green",
                    )

                    if failed_copies:
                        console.print(
                            f"❌ Failed to copy: {len(failed_copies)} tables",
                            style="red",
                        )
                        console.print(
                            f"   Failed tables: {', '.join(failed_copies)}", style="red"
                        )
                        return False

                    # Show verification of copied data
                    console.print(
                        f"🔍 Verification - Table counts in {target_schema}:",
                        style="cyan",
                    )
                    for table in table_list:
                        if table not in failed_copies:
                            try:
                                cursor.execute(
                                    f"SELECT COUNT(*) FROM {target_schema.upper()}.{table.upper()}"
                                )
                                count = cursor.fetchone()[0]
                                console.print(
                                    f"   {table}: {count:,} rows", style="blue"
                                )
                            except oracledb.Error:
                                pass

                    return True

        except Exception as e:
            console.print(f"❌ Error copying schema: {e}", style="red")
            return False


# Global database manager instance
db_manager = DatabaseManager()
