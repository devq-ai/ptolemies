#!/usr/bin/env python3
"""
Setup script for Neo4j MCP Server
"""

from setuptools import setup, find_packages

setup(
    name="neo4j-mcp-server",
    version="1.0.0",
    description="Neo4j MCP Server for DevQ.AI ecosystem",
    author="DevQ.AI Team",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "neo4j>=5.0.0",
        "logfire",
        "mcp"
    ],
    entry_points={
        "console_scripts": [
            "neo4j-mcp-server=neo4j_mcp_server:main"
        ]
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
    ]
)