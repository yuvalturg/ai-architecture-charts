"""Command Line Interface for TPC-DS utility."""

import sys
from pathlib import Path

import click
import yaml
from rich.console import Console
from rich.table import Table

from .config import config_manager
from .database import db_manager
from .generator import DataGenerator
from .loader import DataLoader

console = Console()


@click.group()
@click.version_option()
def cli():
    """TPC-DS Utility - Generate synthetic TPC-DS data and manage Oracle databases.

    By default, operations use your current database user's schema. To target a different
    schema, use the --schema option (requires appropriate database privileges).
    """
    pass


@cli.group()
def config():
    """Manage configuration settings."""
    pass


@config.command("show")
def config_show():
    """Show current configuration."""
    cfg = config_manager.load()

    table = Table(title="TPC-DS Utility Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")

    # Database settings
    table.add_row("Database Host", cfg.database.host)
    table.add_row("Database Port", str(cfg.database.port))
    table.add_row("Service Name", cfg.database.service_name)
    table.add_row("Username", cfg.database.username or "[Not Set]")
    table.add_row("Password", "***" if cfg.database.password else "[Not Set]")

    # TPC-DS settings
    table.add_row("Schema Name", cfg.schema_name or "[Current User Schema]")
    table.add_row("Default Scale", str(cfg.default_scale))
    table.add_row("Output Directory", cfg.default_output_dir)
    table.add_row("Parallel Workers", str(cfg.parallel_workers))

    console.print(table)


@config.command("set")
@click.option("--host", help="Database host")
@click.option("--port", type=int, help="Database port")
@click.option("--service-name", help="Database service name or SID")
@click.option("--username", help="Database username")
@click.option("--password", help="Database password")
@click.option("--use-sid", is_flag=True, help="Use SID instead of service name")
@click.option("--schema-name", help="Target schema name for TPC-DS tables")
@click.option("--default-scale", type=int, help="Default scale factor")
@click.option("--output-dir", help="Default output directory")
@click.option("--parallel-workers", type=int, help="Number of parallel workers")
def config_set(**kwargs):
    """Set configuration values."""
    # Filter out None values
    updates = {k: v for k, v in kwargs.items() if v is not None}

    if not updates:
        click.echo("No configuration changes specified.")
        return

    config_manager.update(**updates)
    console.print("Configuration updated successfully", style="green")


@config.command("init")
def config_init():
    """Initialize configuration with prompts."""
    click.echo("Setting up TPC-DS Utility configuration...")

    # Database configuration
    host = click.prompt("Database host", default="localhost")
    port = click.prompt("Database port", default=1521, type=int)
    service_name = click.prompt("Database service name", default="orcl")
    username = click.prompt("Database username")

    # Schema settings
    click.echo("\nSchema Configuration:")
    click.echo("• Leave empty to use your current user's schema (recommended)")
    click.echo("• Specify a schema name to create tables in a different schema")
    click.echo("• Note: Different schemas require additional database privileges")
    schema_name = click.prompt(
        "Target schema name (optional)", default="", show_default=False
    )

    # Other settings
    scale = click.prompt("Default scale factor", default=1, type=int)
    output_dir = click.prompt("Default output directory", default="./tpcds_data")
    workers = click.prompt("Parallel workers", default=4, type=int)

    config_manager.update(
        host=host,
        port=port,
        service_name=service_name,
        username=username,
        schema_name=schema_name,
        default_scale=scale,
        default_output_dir=output_dir,
        parallel_workers=workers,
    )

    console.print("Configuration initialized successfully", style="green")


@cli.group()
def db():
    """Database operations."""
    pass


@db.command("test")
def db_test():
    """Test database connection."""
    console.print("Testing database connection...")

    if db_manager.test_connection():
        console.print("Database connection successful", style="green")
    else:
        console.print("Database connection failed", style="red")
        click.echo(
            "Please check your configuration with 'tpcds-util config show'", err=True
        )
        sys.exit(1)


@db.command("grant")
@click.option("--user", required=True, help="Username to grant SELECT privileges to")
def db_grant(user):
    """Grant SELECT on all tables in current schema to a user."""
    console.print(f"Granting SELECT on all tables to {user}...")

    try:
        grant_count = 0
        with db_manager.get_connection() as conn:
            with conn.cursor() as cursor:
                # Get all tables in current schema
                cursor.execute("SELECT table_name FROM user_tables")
                tables = cursor.fetchall()

                if not tables:
                    console.print("No tables found in current schema", style="yellow")
                    return

                # Grant SELECT on each table
                for (table_name,) in tables:
                    try:
                        cursor.execute(f"GRANT SELECT ON {table_name} TO {user}")
                        grant_count += 1
                    except Exception as e:
                        console.print(
                            f"Warning: Could not grant on {table_name}: {e}",
                            style="yellow",
                        )

                conn.commit()

        console.print(
            f"Successfully granted SELECT on {grant_count} tables to {user}",
            style="green",
        )
    except Exception as e:
        console.print(f"Failed to grant privileges: {e}", style="red")
        sys.exit(1)


@db.command("info")
@click.option("--schema", help="Target schema name (overrides config)")
def db_info(schema):
    """Show database table information.

    Shows TPC-DS tables from your current user's schema by default.
    Use --schema to query a different schema.
    """
    tables = db_manager.get_table_info(schema)

    if not tables:
        schema_msg = f" in schema {schema}" if schema else ""
        console.print(
            f"No TPC-DS tables found{schema_msg}. Create schema first with 'tpcds-util schema create'",
            style="yellow",
        )
        return

    schema_title = f"TPC-DS Tables{' (Schema: ' + schema + ')' if schema else ''}"
    table = Table(title=schema_title)
    table.add_column("Table Name", style="cyan")
    table.add_column("Rows", justify="right", style="green")
    table.add_column("Blocks", justify="right")
    table.add_column("Avg Row Length", justify="right")

    for t in tables:
        table.add_row(
            t["TABLE_NAME"],
            str(t["NUM_ROWS"]) if t["NUM_ROWS"] else "0",
            str(t["BLOCKS"]) if t["BLOCKS"] else "0",
            str(t["AVG_ROW_LEN"]) if t["AVG_ROW_LEN"] else "0",
        )

    console.print(table)


@cli.group()
def generate():
    """Data generation operations."""
    pass


@generate.command("data")
@click.option("--scale", type=int, help="Scale factor (default from config)")
@click.option(
    "--output-dir", type=click.Path(), help="Output directory (default from config)"
)
@click.option("--parallel", type=int, help="Parallel workers (default from config)")
def generate_data(scale, output_dir, parallel):
    """Generate synthetic TPC-DS data files."""
    generator = DataGenerator()

    if generator.generate_data(scale, output_dir, parallel):
        console.print("Data generation completed", style="green")
    else:
        console.print("Data generation failed", style="red")
        sys.exit(1)


@cli.group()
def load():
    """Data loading operations."""
    pass


@load.command("data")
@click.option(
    "--data-dir", type=click.Path(exists=True), help="Directory containing data files"
)
@click.option("--parallel", type=int, help="Parallel workers (default from config)")
@click.option("--table", help="Load specific table only")
@click.option(
    "--schema",
    help="Target schema name (overrides config). Must already exist with proper privileges.",
)
@click.option(
    "--schema-file",
    type=click.Path(exists=True),
    help="Path to SQL file for creating tables (auto-creates tables before loading)",
)
def load_data(data_dir, parallel, table, schema, schema_file):
    """Load synthetic data into TPC-DS tables.

    Automatically creates tables before loading if --schema-file is provided.
    Loads data into configured schema or current user's schema by default.

    Examples:
      tpcds-util load data --schema-file schema.sql  # Create tables and load
      tpcds-util load data                            # Load into existing tables
      tpcds-util load data --table store_sales        # Load specific table only
    """
    loader = DataLoader()

    schema_path = Path(schema_file) if schema_file else None

    if loader.load_data(data_dir, parallel, table, schema, schema_path):
        console.print("Data loading completed", style="green")
    else:
        console.print("Data loading failed", style="red")
        sys.exit(1)


@load.command("truncate")
@click.option("--confirm", is_flag=True, help="Skip confirmation prompt")
@click.option(
    "--schema",
    help="Target schema name (overrides config). Requires DELETE privileges.",
)
def truncate_data(confirm, schema):
    """Truncate all TPC-DS tables (remove all data).

    Truncates tables in your current user's schema by default.
    Use --schema to target a different schema (requires database privileges).
    """
    loader = DataLoader()

    if loader.truncate_tables(confirm, schema):
        console.print("Data truncation completed", style="green")
    else:
        console.print("Data truncation failed", style="red")
        sys.exit(1)


@cli.command("status")
def status():
    """Show overall system status."""
    console.print("TPC-DS Utility Status", style="bold blue")
    console.print()

    # Configuration status
    cfg = config_manager.load()
    if cfg.database.username:
        console.print("Configuration: Complete", style="green")
    else:
        console.print("Configuration: Incomplete", style="yellow")

    # Database connection
    if db_manager.test_connection():
        console.print("Database: Connected", style="green")
    else:
        console.print("Database: Connection failed", style="red")

    # Schema status
    tables = db_manager.get_table_info()
    if tables:
        console.print(f"Schema: {len(tables)} tables found", style="green")
    else:
        console.print("Schema: No tables found", style="yellow")


def main():
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()
