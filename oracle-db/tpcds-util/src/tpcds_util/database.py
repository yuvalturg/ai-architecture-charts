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

            console.print(f"Successfully executed {sql_file.name}", style="green")
            return True

        except Exception as e:
            click.echo(f"Error executing SQL file {sql_file}: {e}", err=True)
            return False

    def create_schema(
        self, schema_file: Optional[Path] = None, schema_override: Optional[str] = None
    ) -> bool:
        """Create TPC-DS tables in the specified schema.

        Note: The schema/user must already exist with appropriate privileges.
        Use --schema to target a specific schema, or omit to use current user's schema.
        """
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

        # Create tables in target schema
        if schema_name:
            console.print(
                f"Creating TPC-DS tables from {schema_file} in schema {schema_name}",
                style="cyan",
            )
        else:
            console.print(
                f"Creating TPC-DS tables from {schema_file} in current user's schema",
                style="cyan",
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
                            f"Successfully dropped {dropped_count} tables",
                            style="green",
                        )

                    if failed_tables:
                        console.print(
                            f"Failed to drop {len(failed_tables)} tables: {', '.join(failed_tables)}",
                            style="yellow",
                        )
                        console.print(
                            "Tip: You may need DBA privileges to drop tables in other schemas",
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


# Global database manager instance
db_manager = DatabaseManager()
