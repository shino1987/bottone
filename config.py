"""Configuration settings for the trading bot."""

class Config:
    """Configuration class for trading bot settings."""
    
    # Trading mode
    DRY_RUN = True  # Set to False for live trading
    
    # Binance API credentials (set in environment or update here)
    API_KEY = ""
    API_SECRET = ""
    
    # Trading parameters
    DEFAULT_POSITION_SIZE = 100  # Default position size in USD
    
    # Monitoring intervals
    SIGNAL_CHECK_INTERVAL = 10  # Seconds between position checks
    MONITOR_UPDATE_INTERVAL = 30  # Seconds between signal updates
