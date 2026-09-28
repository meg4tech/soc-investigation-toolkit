"""Allow the toolkit to be run with ``python -m soc_toolkit``."""

import sys

from .cli import main

sys.exit(main())
