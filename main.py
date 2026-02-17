"""
Main entry point for the Binance trading bot.
"""

import logging
import sys

from config import Config
from binance_api import BinanceAPI
from bot import TradingBot
from filters.base_filter import SimpleFilter
from filters.buyside_liquidity import BuysideLiquidityFilter


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
    
    # Define 20 USDC trading pairs for multi-pair support
    usdc_pairs = [
        'BTCUSDC', 'ETHUSDC', 'BNBUSDC', 'ADAUSDC', 'DOGEUSDC',
        'XRPUSDC', 'DOTUSDC', 'UNIUSDC', 'LTCUSDC', 'LINKUSDC',
        'SOLUSDC', 'MATICUSDC', 'AVAXUSDC', 'ATOMUSDC', 'ETCUSDC',
        'ALGOUSDC', 'XLMUSDC', 'VETUSDC', 'ICPUSDC', 'FILUSDC'
    ]
    
    logger.info(f"Configured {len(usdc_pairs)} USDC trading pairs")
    
    # Initialize filters
    # Use BuysideLiquidityFilter for step 1 of the strategy
    filters = [
        BuysideLiquidityFilter(params={
            'swing_period': 5,
            'min_swing_count': 5,
            'volume_threshold': 1.2
        })
    ]
    
    logger.info(f"Loaded {len(filters)} filter(s)")
    for filter_instance in filters:
        logger.info(f"  - {filter_instance.get_description()}")
    
    # Initialize trading bot with multi-pair support
    bot = TradingBot(api=api, filters=filters, symbols=usdc_pairs)
    
    # Set leverage (for cross margin, this is informational)
    for symbol in usdc_pairs:
        api.set_leverage(symbol, Config.LEVERAGE)
    
    # Display bot status
    status = bot.get_status()
    logger.info("=" * 60)
    logger.info("Bot Status:")
    logger.info(f"  Primary Symbol: {status['symbol']}")
    logger.info(f"  Total Pairs: {len(status['symbols'])}")
    logger.info(f"  Leverage: {status['leverage']}x")
    logger.info(f"  Dry Run: {status['dry_run']}")
    logger.info(f"  Filters: {status['filters_count']}")
    logger.info("=" * 60)
    
    # Log state machine initialization
    logger.info("State Machines Initialized:")
    for symbol, state_info in status['states'].items():
        logger.info(f"  {symbol}: {state_info['state_description']}")
    
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
