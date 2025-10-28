#!/usr/bin/env python3
"""Setup script for TPC-DS Utility."""

from setuptools import setup, find_packages
import os

# Read requirements.txt
def read_requirements():
    """Read requirements from requirements.txt file."""
    requirements_path = os.path.join(os.path.dirname(__file__), 'requirements.txt')
    if os.path.exists(requirements_path):
        with open(requirements_path, 'r') as f:
            return [line.strip() for line in f if line.strip() and not line.startswith('#')]
    return []

# Read README for long description
def read_readme():
    """Read README.md for long description."""
    readme_path = os.path.join(os.path.dirname(__file__), 'README.md')
    if os.path.exists(readme_path):
        with open(readme_path, 'r', encoding='utf-8') as f:
            return f.read()
    return ""

setup(
    name="tpcds-util",
    version="1.0.0",
    description="TPC-DS utility for synthetic data generation and Oracle database management",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    author="TPC-DS Utility Team",
    author_email="noreply@example.com",
    url="https://github.com/rhkp/tpcds-util",
    license="Apache-2.0",
    
    # Package configuration
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.8",
    
    # Dependencies
    install_requires=read_requirements(),
    
    # Entry points for CLI
    entry_points={
        'console_scripts': [
            'tpcds-util=tpcds_util.cli:main',
        ],
    },
    
    # Classifiers
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Database",
        "Topic :: Software Development :: Testing",
        "Topic :: System :: Benchmark",
    ],
    
    # Additional metadata
    keywords="tpc-ds database benchmark oracle synthetic-data",
    project_urls={
        "Bug Reports": "https://github.com/rhkp/tpcds-util/issues",
        "Source": "https://github.com/rhkp/tpcds-util",
        "Documentation": "https://github.com/rhkp/tpcds-util/blob/main/README.md",
    },
    
    # Include additional files
    include_package_data=True,
    zip_safe=False,
)