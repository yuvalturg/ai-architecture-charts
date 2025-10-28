"""Data loading utilities for TPC-DS."""

import concurrent.futures
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

import click
import oracledb
from rich.console import Console
from rich.progress import BarColumn, Progress, TextColumn, TimeRemainingColumn

from .config import config_manager
from .database import db_manager

console = Console()


class DataLoader:
    """Handles loading TPC-DS data into Oracle database."""

    # TPC-DS table names and their corresponding data files
    TABLE_FILES = {
        "call_center": "call_center.dat",
        "catalog_page": "catalog_page.dat",
        "catalog_returns": "catalog_returns.dat",
        "catalog_sales": "catalog_sales.dat",
        "customer": "customer.dat",
        "customer_address": "customer_address.dat",
        "customer_demographics": "customer_demographics.dat",
        "date_dim": "date_dim.dat",
        "household_demographics": "household_demographics.dat",
        "income_band": "income_band.dat",
        "inventory": "inventory.dat",
        "item": "item.dat",
        "promotion": "promotion.dat",
        "reason": "reason.dat",
        "ship_mode": "ship_mode.dat",
        "store": "store.dat",
        "store_returns": "store_returns.dat",
        "store_sales": "store_sales.dat",
        "time_dim": "time_dim.dat",
        "warehouse": "warehouse.dat",
        "web_page": "web_page.dat",
        "web_returns": "web_returns.dat",
        "web_sales": "web_sales.dat",
        "web_site": "web_site.dat",
    }

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

    def _find_data_files(self, data_dir: str) -> Dict[str, Path]:
        """Find available data files in the directory."""
        data_path = Path(data_dir)

        if not data_path.exists():
            click.echo(f"Data directory not found: {data_dir}", err=True)
            return {}

        found_files = {}
        for table, filename in self.TABLE_FILES.items():
            file_path = data_path / filename
            if file_path.exists():
                found_files[table] = file_path

        return found_files

    def _generate_control_file(
        self,
        table: str,
        data_file: Path,
        control_dir: Path,
        schema_override: Optional[str] = None,
    ) -> Path:
        """Generate Oracle SQL*Loader control file for a table."""
        control_file = control_dir / f"{table}.ctl"
        schema_name = self._get_schema_name(schema_override)
        qualified_table = self._qualify_table_name(table, schema_name)

        # Basic control file template - would need to be customized per table
        control_content = f"""LOAD DATA
INFILE '{data_file.absolute()}'
APPEND INTO TABLE {qualified_table}
FIELDS TERMINATED BY '|'
TRAILING NULLCOLS
(
    -- Column definitions would go here
    -- This is a simplified template
)
"""

        with open(control_file, "w") as f:
            f.write(control_content)

        return control_file

    def _load_table_sqlldr(
        self, table: str, data_file: Path, control_file: Path
    ) -> bool:
        """Load a single table using SQL*Loader."""
        cfg = self.config.database
        password = config_manager.get_password()

        # Build SQL*Loader command
        userid = f"{cfg.username}/{password}@{cfg.dsn}"

        cmd = [
            "sqlldr",
            f"userid={userid}",
            f"control={control_file}",
            "errors=10000",
            "silent=header,feedback",
        ]

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=3600  # 1 hour timeout
            )

            if result.returncode == 0:
                return True
            else:
                click.echo(f"SQL*Loader failed for {table}: {result.stderr}", err=True)
                return False

        except subprocess.TimeoutExpired:
            click.echo(f"SQL*Loader timeout for table {table}", err=True)
            return False
        except Exception as e:
            click.echo(f"Error loading {table}: {e}", err=True)
            return False

    def _load_table_direct(
        self, table: str, data_file: Path, schema_override: Optional[str] = None
    ) -> bool:
        """Load table using direct Oracle connection (for smaller tables)."""
        schema_name = self._get_schema_name(schema_override)
        qualified_table = self._qualify_table_name(table, schema_name)

        try:
            with db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    # First, get the table structure with data types
                    try:
                        if schema_name:
                            cursor.execute(
                                "SELECT column_name, data_type FROM all_tab_columns WHERE owner = :schema_name AND table_name = :table_name ORDER BY column_id",
                                {
                                    "schema_name": schema_name,
                                    "table_name": table.upper(),
                                },
                            )
                        else:
                            cursor.execute(
                                "SELECT column_name, data_type FROM user_tab_columns WHERE table_name = :table_name ORDER BY column_id",
                                {"table_name": table.upper()},
                            )
                        table_structure = cursor.fetchall()
                        columns = [row[0] for row in table_structure]
                        column_types = {row[0]: row[1] for row in table_structure}

                        if not columns:
                            console.print(
                                f"Table {table.upper()} not found in database",
                                style="red",
                            )
                            console.print(
                                f"❌ Need to create table {table.upper()} first with schema create command",
                                style="red",
                            )
                            return False  # Fail if table doesn't exist

                    except oracledb.Error as e:
                        console.print(
                            f"Could not get structure for table {table.upper()}: {e}",
                            style="red",
                        )
                        return False  # Fail on error instead of skipping

                    # Read and insert data in batches for better performance
                    rows_inserted = 0
                    batch_size = 1000
                    batch_data = []

                    # Prepare bulk insert statement
                    placeholder_template = []
                    for i, col_name in enumerate(columns):
                        if column_types[col_name] == "DATE":
                            placeholder_template.append(
                                "TO_DATE(:v" + str(i + 1) + ", 'YYYY-MM-DD')"
                            )
                        else:
                            placeholder_template.append(":v" + str(i + 1))

                    insert_sql = f"INSERT INTO {qualified_table} ({','.join(columns)}) VALUES ({','.join(placeholder_template)})"

                    with open(data_file, "r", encoding="utf-8") as f:
                        for line_num, line in enumerate(f, 1):
                            if line.strip():
                                values = line.strip().split("|")

                                # Remove empty trailing columns (common TPC-DS issue)
                                while values and values[-1] == "":
                                    values.pop()

                                # Ensure we have the right number of columns
                                if len(values) != len(columns):
                                    if (
                                        line_num == 1
                                    ):  # Log column mismatch for first row
                                        console.print(
                                            f"Column mismatch in {table}: data has {len(values)} columns, table has {len(columns)} columns (after cleanup)",
                                            style="yellow",
                                        )

                                    # Pad with NULL values if needed
                                    while len(values) < len(columns):
                                        values.append("")
                                    # Truncate if too many values
                                    if len(values) > len(columns):
                                        values = values[: len(columns)]
                                        if line_num == 1:
                                            console.print(
                                                f"Truncated extra columns for {table}",
                                                style="yellow",
                                            )

                                # Process values for batch insert
                                processed_values = []

                                for v, col_name in zip(values, columns):
                                    if not v:  # Empty value
                                        processed_values.append(None)
                                    elif column_types[col_name] == "DATE":
                                        # Handle date conversion
                                        if (
                                            v and len(v) == 10 and v.count("-") == 2
                                        ):  # YYYY-MM-DD format
                                            processed_values.append(v)
                                        else:
                                            processed_values.append(None)
                                    elif column_types[col_name] == "NUMBER":
                                        # Handle number conversion
                                        try:
                                            num_val = float(v) if "." in v else int(v)
                                            processed_values.append(num_val)
                                        except ValueError:
                                            processed_values.append(None)
                                    else:
                                        # String values
                                        processed_values.append(v)

                                batch_data.append(processed_values)

                                # Execute batch when it reaches batch_size
                                if len(batch_data) >= batch_size:
                                    try:
                                        cursor.executemany(insert_sql, batch_data)
                                        rows_inserted += len(batch_data)
                                        conn.commit()

                                        # Progress update
                                        if rows_inserted % 5000 == 0:
                                            console.print(
                                                f"  Loaded {rows_inserted:,} rows into {table.upper()}",
                                                style="cyan",
                                            )

                                    except oracledb.Error as e:
                                        # Fallback to individual inserts for this batch
                                        console.print(
                                            f"Batch insert failed, trying individual inserts: {str(e)[:100]}",
                                            style="yellow",
                                        )
                                        for row_data in batch_data:
                                            try:
                                                cursor.execute(insert_sql, row_data)
                                                rows_inserted += 1
                                            except oracledb.Error:
                                                pass  # Skip problematic rows
                                        conn.commit()

                                    batch_data = []  # Reset batch

                        # Insert remaining rows in final batch
                        if batch_data:
                            try:
                                cursor.executemany(insert_sql, batch_data)
                                rows_inserted += len(batch_data)
                                conn.commit()
                            except oracledb.Error as e:
                                # Fallback to individual inserts
                                console.print(
                                    f"Final batch insert failed, trying individual inserts: {str(e)[:100]}",
                                    style="yellow",
                                )
                                for row_data in batch_data:
                                    try:
                                        cursor.execute(insert_sql, row_data)
                                        rows_inserted += 1
                                    except oracledb.Error:
                                        pass
                                conn.commit()

                    # Final commit
                    conn.commit()
                    console.print(
                        f"Inserted {rows_inserted} rows into {qualified_table}",
                        style="green",
                    )
                    return rows_inserted > 0

        except Exception as e:
            click.echo(f"Error loading {table} directly: {e}", err=True)
            return False

    def load_data(
        self,
        data_dir: Optional[str] = None,
        parallel: Optional[int] = None,
        table: Optional[str] = None,
        schema_override: Optional[str] = None,
    ) -> bool:
        """Load TPC-DS data into database."""

        data_dir = data_dir or self.config.default_output_dir
        parallel = parallel or self.config.parallel_workers

        # Find available data files
        data_files = self._find_data_files(data_dir)

        if not data_files:
            click.echo(f"No TPC-DS data files found in {data_dir}", err=True)
            click.echo("Generate data first with: tpcds-util generate data", err=True)
            return False

        # Filter to specific table if requested
        if table:
            if table.lower() in data_files:
                data_files = {table.lower(): data_files[table.lower()]}
            else:
                click.echo(f"Table {table} not found in data files", err=True)
                return False

        console.print(f"Loading {len(data_files)} tables from {data_dir}")

        # Create control files directory
        control_dir = Path(data_dir) / "control_files"
        control_dir.mkdir(exist_ok=True)

        # Test database connection first
        if not db_manager.test_connection():
            click.echo("Database connection failed", err=True)
            return False

        # Load tables
        success_count = 0

        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("{task.completed}/{task.total}"),
            TimeRemainingColumn(),
            console=console,
        ) as progress:

            if parallel > 1:
                # Parallel loading
                task = progress.add_task(
                    "Loading tables (parallel)...", total=len(data_files)
                )

                with concurrent.futures.ThreadPoolExecutor(
                    max_workers=parallel
                ) as executor:
                    futures = {}

                    for table_name, data_file in data_files.items():
                        # For demo purposes, using direct loading
                        # In production, would use SQL*Loader with proper control files
                        future = executor.submit(
                            self._load_table_direct,
                            table_name,
                            data_file,
                            schema_override,
                        )
                        futures[future] = table_name

                    for future in concurrent.futures.as_completed(futures):
                        table_name = futures[future]
                        try:
                            success = future.result()
                            if success:
                                success_count += 1
                                console.print(f"✅ Loaded {table_name}", style="green")
                            else:
                                console.print(
                                    f"❌ Failed to load {table_name}", style="red"
                                )
                        except Exception as e:
                            console.print(
                                f"❌ Error loading {table_name}: {e}", style="red"
                            )

                        progress.advance(task)

            else:
                # Sequential loading
                task = progress.add_task(
                    "Loading tables (sequential)...", total=len(data_files)
                )

                for table_name, data_file in data_files.items():
                    console.print(f"Loading {table_name}...")

                    # For demo purposes, using direct loading
                    success = self._load_table_direct(
                        table_name, data_file, schema_override
                    )

                    if success:
                        success_count += 1
                        console.print(f"✅ Loaded {table_name}", style="green")
                    else:
                        console.print(f"❌ Failed to load {table_name}", style="red")

                    progress.advance(task)

        # Summary
        if success_count == len(data_files):
            console.print(
                f"✅ All {success_count} tables loaded successfully", style="green"
            )
            return True
        else:
            console.print(
                f"⚠️  {success_count}/{len(data_files)} tables loaded successfully",
                style="yellow",
            )
            return False

    def truncate_tables(
        self, confirm: bool = False, schema_override: Optional[str] = None
    ) -> bool:
        """Truncate all TPC-DS tables."""
        schema_name = self._get_schema_name(schema_override)

        if not confirm:
            schema_msg = f" in schema {schema_name}" if schema_name else ""
            if not click.confirm(
                f"This will delete all data from TPC-DS tables{schema_msg}. Continue?"
            ):
                click.echo("Operation cancelled.")
                return False

        tables = list(self.TABLE_FILES.keys())

        try:
            with db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    with Progress(
                        TextColumn("[progress.description]{task.description}"),
                        BarColumn(),
                        console=console,
                    ) as progress:
                        task = progress.add_task(
                            "Truncating tables...", total=len(tables)
                        )

                        for table in tables:
                            try:
                                qualified_table = self._qualify_table_name(
                                    table, schema_name
                                )
                                cursor.execute(f"TRUNCATE TABLE {qualified_table}")
                                progress.advance(task)
                            except oracledb.Error as e:
                                if "ORA-00942" not in str(e):  # Table doesn't exist
                                    console.print(
                                        f"Warning truncating {table}: {e}",
                                        style="yellow",
                                    )
                                progress.advance(task)

                        conn.commit()

            console.print("✅ Tables truncated successfully", style="green")
            return True

        except Exception as e:
            click.echo(f"Error truncating tables: {e}", err=True)
            return False
