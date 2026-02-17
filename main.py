"""
Main entry point for the Binance trading bot.
"""

import logging
import sys

from config import Config
from binance_api import BinanceAPI
from bot import TradingBot
from filters.base_filter import SimpleFilter


def setup_logging():
    """Setup logging configuration."""
    log_level = Config.get_log_level()
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('trading_bot.log')
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info("Logging initialized")
    return logger


def main():
    """Main function to start the trading bot."""
    # Setup logging
    logger = setup_logging()
    
    logger.info("=" * 60)
    logger.info("Starting Binance Trading Bot")
    logger.info("=" * 60)
    
    # Display and validate configuration
    Config.display_config()
    
    if not Config.validate():
        logger.error("Configuration validation failed")
        sys.exit(1)
    
    # Initialize Binance API
    try:
        api = BinanceAPI(
            api_key=Config.BINANCE_API_KEY,
            api_secret=Config.BINANCE_API_SECRET,
            testnet=False
        )
        logger.info("Binance API initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Binance API: {e}")
        sys.exit(1)
    
    # Test API connection
    balance = api.get_account_balance()
    if balance:
        logger.info("API connection test successful")
    else:
        logger.error("API connection test failed")
        if not Config.DRY_RUN:
            sys.exit(1)
    
    # Initialize filters
    # For now, we use a simple example filter
    # Users can add their own filters here
    filters = [
        SimpleFilter()
    ]
    
    logger.info(f"Loaded {len(filters)} filter(s)")
    for filter_instance in filters:
        logger.info(f"  - {filter_instance.get_description()}")
    
    # Initialize trading bot
    bot = TradingBot(api=api, filters=filters)
    
    # Set leverage (for cross margin, this is informational)
    api.set_leverage(Config.TRADING_PAIR, Config.LEVERAGE)
    
    # Display bot status
    status = bot.get_status()
    logger.info("=" * 60)
    logger.info("Bot Status:")
    logger.info(f"  Symbol: {status['symbol']}")
    logger.info(f"  Leverage: {status['leverage']}x")
    logger.info(f"  Dry Run: {status['dry_run']}")
    logger.info(f"  Filters: {status['filters_count']}")
    logger.info("=" * 60)
    
    # Start the bot
    try:
        # Run indefinitely with 60 second intervals
        # For testing, you can pass iterations parameter: bot.run(iterations=10)
        bot.run(interval=60)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user (Ctrl+C)")
    except Exception as e:
        logger.error(f"Bot crashed: {e}", exc_info=True)
        sys.exit(1)
    
    logger.info("Bot shutdown complete")


if __name__ == "__main__":
    main()
