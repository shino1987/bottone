"""
Main entry point for the Binance trading bot.
"""

import logging
import sys
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


def main():
    """Main function to start the trading bot."""
    # Setup logging
    logger = setup_logging()
    
    logger.info("=" * 60)
    logger.info("Starting Binance Trading Bot - Multi-Pair Monitor")
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
    
    # Initialize multi-pair monitor
    logger.info(f"Initializing multi-pair monitor with {len(Config.TRADING_PAIRS)} pairs")
    monitor = MultiPairMonitor(
        api=api,
        trading_pairs=Config.TRADING_PAIRS,
        interval=Config.TIMEFRAME,
        kline_limit=Config.KLINE_LIMIT,
        check_interval=Config.CHECK_INTERVAL_SECONDS
    )
    
    # Initialize trading bot for executing trades
    filters = [SimpleFilter()]
    bot = TradingBot(api=api, filters=filters)
    
    logger.info("=" * 60)
    logger.info(f"Multi-Pair Monitor Configuration:")
    logger.info(f"  Trading Pairs: {len(Config.TRADING_PAIRS)}")
    logger.info(f"  Timeframe: {Config.TIMEFRAME}")
    logger.info(f"  Kline Limit: {Config.KLINE_LIMIT}")
    logger.info(f"  Check Interval: {Config.CHECK_INTERVAL_SECONDS}s")
    logger.info(f"  Step Timeout: {Config.STEP_TIMEOUT_MINUTES} minutes")
    logger.info(f"  Risk per Trade: {Config.RISK_PER_TRADE_PERCENT}%")
    logger.info(f"  Risk/Reward Ratio: {Config.RISK_REWARD_RATIO}:1")
    logger.info(f"  DRY RUN: {Config.DRY_RUN}")
    logger.info("=" * 60)
    
    # Start the monitor
    try:
        monitor.start()
        logger.info("Multi-pair monitor started successfully")
        
        # Main loop: check for entries and display dashboard
        logger.info("Entering main monitoring loop...")
        iteration = 0
        
        while True:
            try:
                # Check for new entries
                entry = monitor.get_next_entry()
                if entry:
                    logger.info("=" * 60)
                    logger.info("NEW ENTRY SIGNAL DETECTED!")
                    logger.info(f"  Symbol: {entry['symbol']}")
                    logger.info(f"  Entry Price: {entry['entry']:.2f}")
                    logger.info(f"  Stop Loss: {entry['stop_loss']:.2f}")
                    logger.info(f"  Take Profit: {entry['take_profit']:.2f}")
                    logger.info(f"  Risk/Reward: {entry['risk_reward']:.1f}")
                    logger.info(f"  Timestamp: {entry['timestamp']}")
                    logger.info("=" * 60)
                    
                    # In production, execute the trade here
                    if not Config.DRY_RUN:
                        # Calculate position size based on risk
                        # Execute order through bot
                        logger.info(f"Executing trade for {entry['symbol']}")
                        # bot.open_position('BUY', entry['entry'])
                    else:
                        logger.info("[DRY RUN] Would execute trade")
                    
                    # Reset state machine for this pair after trade
                    monitor.reset_pair_state(entry['symbol'])
                
                # Display dashboard every 10 iterations (10 minutes with 60s interval)
                iteration += 1
                if iteration % 10 == 0:
                    dashboard = monitor.get_dashboard_data()
                    logger.info("\n" + dashboard)
                    
                    # Also log statistics
                    stats = monitor.get_statistics()
                    logger.info(f"Queue size: {stats['entry_queue_size']}")
                
                time.sleep(60)  # Check every minute
                
            except KeyboardInterrupt:
                logger.info("Received interrupt signal")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}", exc_info=True)
                time.sleep(60)
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user (Ctrl+C)")
    except Exception as e:
        logger.error(f"Bot crashed: {e}", exc_info=True)
        sys.exit(1)
    finally:
        # Stop monitor
        logger.info("Stopping monitor...")
        monitor.stop()
        logger.info("Bot shutdown complete")


if __name__ == "__main__":
    main()
