"""Command Line Interface for TPC-DS utility."""

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
    console.print("✅ Configuration updated successfully", style="green")


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

    console.print("✅ Configuration initialized successfully", style="green")


@cli.group()
def db():
    """Database operations."""
    pass


@db.command("test")
def db_test():
    """Test database connection."""
    console.print("Testing database connection...")

    if db_manager.test_connection():
        console.print("✅ Database connection successful", style="green")
    else:
        console.print("❌ Database connection failed", style="red")
        click.echo(
            "Please check your configuration with 'tpcds-util config show'", err=True
        )


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
def schema():
    """Schema management operations."""
    pass


@schema.command("create")
@click.option(
    "--schema-file", type=click.Path(exists=True), help="Path to schema SQL file"
)
@click.option(
    "--schema",
    help="Target schema name (overrides config). Requires CREATE [ANY] TABLE privileges.",
)
def schema_create(schema_file, schema):
    """Create TPC-DS schema.

    Creates TPC-DS tables in your current user's schema by default.
    Use --schema to target a different schema (requires database privileges).

    Examples:
      tpcds-util schema create                    # Use current user's schema
      tpcds-util schema create --schema TPCDSV1  # Use specific schema (needs privileges)
    """
    schema_path = Path(schema_file) if schema_file else None

    if db_manager.create_schema(schema_path, schema):
        console.print("✅ Schema created successfully", style="green")
    else:
        console.print("❌ Schema creation failed", style="red")


@schema.command("drop")
@click.option("--confirm", is_flag=True, help="Skip confirmation prompt")
@click.option(
    "--schema",
    help="Target schema name (overrides config). Requires DROP [ANY] TABLE privileges.",
)
def schema_drop(confirm, schema):
    """Drop TPC-DS tables (not the schema itself).

    Drops all TPC-DS tables from your current user's schema by default.
    Use --schema to target a different schema (requires database privileges).

    Note: This only removes TPC-DS tables, not the Oracle schema/user itself.

    Examples:
      tpcds-util schema drop                      # Drop tables from current user's schema
      tpcds-util schema drop --schema TPCDSV1    # Drop tables from specific schema (needs privileges)
    """
    if db_manager.drop_schema(confirm, schema):
        console.print("✅ TPC-DS tables dropped successfully", style="green")
    else:
        console.print("❌ TPC-DS tables drop failed", style="red")


@schema.group()
def user():
    """Oracle user/schema management operations."""
    pass


@user.command("create")
@click.argument("username")
@click.option(
    "--password", help="Password for the new user (will prompt if not provided)"
)
@click.option(
    "--tablespace",
    default="UNLIMITED",
    help="Tablespace privileges (default: UNLIMITED)",
)
def user_create(username, password, tablespace):
    """Create a new Oracle user/schema.

    Creates a new Oracle user with CONNECT, RESOURCE privileges and tablespace access.
    Requires DBA privileges or CREATE USER system privilege.

    Examples:
      tpcds-util schema user create sales              # Creates 'sales' user (prompts for password)
      tpcds-util schema user create sales --password mypass123  # Creates with specified password
    """
    if not password:
        password = click.prompt(f"Password for user '{username}'", hide_input=True)

    if db_manager.create_user(username, password, tablespace):
        console.print(f"✅ User '{username}' created successfully", style="green")
    else:
        console.print(f"❌ Failed to create user '{username}'", style="red")


@user.command("restrict")
@click.argument("username")
def user_restrict(username):
    """Restrict a user by removing dangerous system privileges.

    Removes system privileges like CREATE TABLE, CREATE INDEX, etc. but cannot
    prevent DML operations (INSERT/UPDATE/DELETE) on tables the user owns.
    This reduces the damage scope for AI/MCP server usage.

    Note: Oracle table owners always retain full DML access to their own tables.

    Examples:
      tpcds-util schema user restrict sales    # Remove dangerous privileges from sales user
    """
    if db_manager.restrict_user_privileges(username):
        console.print(f"✅ User '{username}' privileges restricted", style="green")
        console.print("   Removed dangerous system privileges", style="dim")
        console.print(
            "   User can still modify their own tables (Oracle limitation)", style="dim"
        )
    else:
        console.print(
            f"❌ Failed to restrict user '{username}' privileges", style="red"
        )


@schema.command("copy")
@click.argument("source_schema")
@click.argument("target_schema")
@click.option(
    "--tables",
    help="Comma-separated list of tables to copy (copies all TPC-DS tables if not specified)",
)
@click.option(
    "--structure-only", is_flag=True, help="Copy table structure only, no data"
)
def schema_copy(source_schema, target_schema, tables, structure_only):
    """Copy tables from one schema to another.

    Copies TPC-DS tables (or specified tables) from source schema to target schema.
    Target schema/user must already exist.

    Examples:
      tpcds-util schema copy SYSTEM sales                    # Copy all TPC-DS tables from SYSTEM to sales
      tpcds-util schema copy SYSTEM sales --tables store_sales,web_sales,catalog_sales  # Copy specific tables
      tpcds-util schema copy SYSTEM sales --structure-only   # Copy table structures only (no data)
    """
    # By default, copy data unless --structure-only is specified
    include_data = not structure_only

    table_list = None
    if tables:
        table_list = [t.strip() for t in tables.split(",")]

    if db_manager.copy_schema(source_schema, target_schema, table_list, include_data):
        action = "structure" if structure_only else "tables and data"
        console.print(
            f"✅ Successfully copied {action} from '{source_schema}' to '{target_schema}'",
            style="green",
        )
    else:
        console.print(
            f"❌ Failed to copy from '{source_schema}' to '{target_schema}'",
            style="red",
        )


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
        console.print("✅ Data generation completed", style="green")
    else:
        console.print("❌ Data generation failed", style="red")


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
    help="Target schema name (overrides config). Requires INSERT privileges.",
)
def load_data(data_dir, parallel, table, schema):
    """Load synthetic data into TPC-DS tables.

    Loads data into your current user's schema by default.
    Use --schema to target a different schema (requires database privileges).

    Examples:
      tpcds-util load data                        # Load into current user's schema
      tpcds-util load data --schema TPCDSV1      # Load into specific schema (needs privileges)
      tpcds-util load data --table store_sales   # Load specific table only
    """
    loader = DataLoader()

    if loader.load_data(data_dir, parallel, table, schema):
        console.print("✅ Data loading completed", style="green")
    else:
        console.print("❌ Data loading failed", style="red")


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
        console.print("✅ Data truncation completed", style="green")
    else:
        console.print("❌ Data truncation failed", style="red")


@cli.command("status")
def status():
    """Show overall system status."""
    console.print("TPC-DS Utility Status", style="bold blue")
    console.print()

    # Configuration status
    cfg = config_manager.load()
    if cfg.database.username:
        console.print("✅ Configuration: Complete", style="green")
    else:
        console.print("⚠️  Configuration: Incomplete", style="yellow")

    # Database connection
    if db_manager.test_connection():
        console.print("✅ Database: Connected", style="green")
    else:
        console.print("❌ Database: Connection failed", style="red")

    # Schema status
    tables = db_manager.get_table_info()
    if tables:
        console.print(f"✅ Schema: {len(tables)} tables found", style="green")
    else:
        console.print("⚠️  Schema: No tables found", style="yellow")


def main():
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()
