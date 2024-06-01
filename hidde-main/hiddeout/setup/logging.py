from logging import INFO, basicConfig, getLogger

# ANSI escape codes for colors
g = "\033[92m"  # green color
r = "\033[0m"   # reset color

# Configure logging
basicConfig(
    level=INFO,
    format=f"{g}[dev/{{module}}]{r} {{message}}",
    datefmt=None,
    style="{",
)

# Example usage
logger = getLogger(__name__)
logger.info("This is a log message")
