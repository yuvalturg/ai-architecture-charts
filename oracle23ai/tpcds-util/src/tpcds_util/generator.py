"""TPC-DS synthetic data generation utilities."""

from pathlib import Path
from typing import Optional

import click
from rich.console import Console

from .config import config_manager

console = Console()


class DataGenerator:
    """Handles TPC-DS synthetic data generation."""

    def __init__(self):
        self.config = config_manager.load()

    def generate_data(
        self,
        scale: Optional[int] = None,
        output_dir: Optional[str] = None,
        parallel: Optional[int] = None,
        synthetic: bool = True,
    ) -> bool:
        """Generate TPC-DS data files using synthetic data generation."""

        # Use defaults from config if not specified
        scale = scale or self.config.default_scale
        output_dir = output_dir or self.config.default_output_dir
        parallel = parallel or self.config.parallel_workers

        # Always use synthetic data generation
        from .synthetic_generator import create_synthetic_data

        console.print("🔬 Generating synthetic TPC-DS compliant data...", style="cyan")
        console.print(
            "📋 This data is license-free and safe for enterprise use", style="green"
        )
        return create_synthetic_data(scale=scale, output_dir=output_dir)

    def list_tables(self) -> None:
        """List all TPC-DS tables that can be generated."""
        tables = [
            "call_center",
            "catalog_page",
            "catalog_returns",
            "catalog_sales",
            "customer",
            "customer_address",
            "customer_demographics",
            "date_dim",
            "household_demographics",
            "income_band",
            "inventory",
            "item",
            "promotion",
            "reason",
            "ship_mode",
            "store",
            "store_returns",
            "store_sales",
            "time_dim",
            "warehouse",
            "web_page",
            "web_returns",
            "web_sales",
            "web_site",
            "dbgen_version",
        ]

        console.print(
            "TPC-DS Tables Available for Synthetic Generation:", style="bold blue"
        )
        console.print()

        for i, table in enumerate(tables, 1):
            console.print(f"{i:2d}. {table}")

        console.print(f"\nTotal: {len(tables)} tables")
        console.print("Use: tpcds-util generate data --synthetic", style="cyan")
