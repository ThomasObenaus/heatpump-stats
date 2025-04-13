"""Configuration module for Viessmann API integration."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Base configuration
CONFIG = {
    # Viessmann API credentials
    "VIESSMANN_USER": os.getenv("VIESSMANN_USER", ""),
    "VIESSMANN_PASSWORD": os.getenv("VIESSMANN_PASSWORD", ""),
    
    # Optional client ID (if needed for API)
    "CLIENT_ID": os.getenv("CLIENT_ID", ""),
    
    # Data storage configuration
    "DATA_DIR": os.getenv("DATA_DIR", str(Path.home() / "heatpump_data")),
    
    # Polling frequency in minutes
    "POLLING_INTERVAL": int(os.getenv("POLLING_INTERVAL", "15")),
    
    # API endpoint details
    "API_BASE_URL": os.getenv("API_BASE_URL", "https://api.viessmann.com"),
}

# Create data directory if it doesn't exist
def init_config():
    """Initialize configuration and create necessary directories."""
    data_dir = Path(CONFIG["DATA_DIR"])
    if not data_dir.exists():
        data_dir.mkdir(parents=True, exist_ok=True)
    
    # Validate required configuration
    if not CONFIG["VIESSMANN_USER"] or not CONFIG["VIESSMANN_PASSWORD"]:
        raise ValueError(
            "Missing Viessmann credentials. Please set VIESSMANN_USER and "
            "VIESSMANN_PASSWORD environment variables or in .env file."
        )

# Check configuration validity
def validate_config():
    """Validate the configuration settings."""
    required_keys = ["VIESSMANN_USER", "VIESSMANN_PASSWORD"]
    missing = [key for key in required_keys if not CONFIG[key]]
    
    if missing:
        raise ValueError(
            f"Missing required configuration: {', '.join(missing)}. "
            "Please check your .env file or environment variables."
        )