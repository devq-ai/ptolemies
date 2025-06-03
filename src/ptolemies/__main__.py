#!/usr/bin/env python3
"""
Main entry point for the Ptolemies Knowledge Base.

This module provides the primary entry point for running the Ptolemies
knowledge base system, including CLI access and server startup.
"""

import sys
import os

# Add the src directory to the Python path for proper imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from .cli import main

if __name__ == "__main__":
    main()