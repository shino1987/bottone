"""
Main entry point for the Binance trading bot.
Supports both single-pair mode with state machine and multi-pair monitoring.
"""

import logging
import sys
import os
import time

from config import Config
from binance_api import BinanceAPI
from bot import TradingBot
from filters.base_filter import SimpleFilter
from multi_pair_monitor import MultiPairMonitor


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


def run_multi_pair_mode(api: BinanceAPI, logger: logging.Logger):
    """
    Run in multi-pair monitoring mode.
    
    Args:
        api: BinanceAPI instance
        logger: Logger instance
    """
    logger.info("=" * 80)
    logger.info("Starting Multi-Pair Monitor Mode")
    logger.info("=" * 80)
    
    # Initialize multi-pair monitor
    monitor = MultiPairMonitor(api)
    
    # Start monitoring
    monitor.start(update_interval=60)  # 60 seconds update interval
    
    logger.info("Multi-pair monitor is running. Press Ctrl+C to stop.")
    
    try:
        # Main loop - check for entry signals
        iteration_count = 0
        while True:
            # Check for entry signals
            entry_signal = monitor.get_next_entry()
            if entry_signal:
                logger.info("=" * 80)
                logger.info(f"ENTRY SIGNAL FOUND!")
                logger.info(f"Symbol: {entry_signal['symbol']}")
                logger.info(f"Timestamp: {entry_signal['timestamp']}")
                logger.info(f"Entry Data: {entry_signal['signal']}")
                logger.info("=" * 80)
                
                # In production, you would execute the trade here
                if Config.DRY_RUN:
                    logger.info("[DRY RUN] Would execute trade here")
                else:
                    logger.info("Execute trade logic here")
            
            # Sleep for 60 seconds between checks
            time.sleep(60)
            
            # Print statistics every 5 iterations (5 minutes)
            iteration_count += 1
            if iteration_count % 5 == 0:
                monitor.print_statistics()
            
    except KeyboardInterrupt:
        logger.info("Stopping multi-pair monitor...")
        monitor.stop()
        logger.info("Multi-pair monitor stopped")


def run_single_pair_mode(api: BinanceAPI, logger: logging.Logger):
    """
    Run in single-pair mode with original bot logic.
    
    Args:
        api: BinanceAPI instance
        logger: Logger instance
    """
    logger.info("=" * 80)
    logger.info("Starting Single-Pair Mode")
    logger.info("=" * 80)
    
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


def main():
    """Main function to start the trading bot."""
    # Setup logging
    logger = setup_logging()
    
    logger.info("=" * 80)
    logger.info("Binance Trading Bot - 7-Step Strategy")
    logger.info("=" * 80)
    
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
    
    # Check mode from environment variable
    mode = os.getenv('BOT_MODE', 'multi-pair').lower()
    
    if mode == 'multi-pair':
        run_multi_pair_mode(api, logger)
    elif mode == 'single-pair':
        run_single_pair_mode(api, logger)
    else:
        logger.error(f"Invalid BOT_MODE: {mode}. Use 'single-pair' or 'multi-pair'")
        sys.exit(1)


if __name__ == "__main__":
    main()
