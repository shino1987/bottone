"""Main trading bot application."""

import logging
import time
import sys
from config import Config
from binance_api import BinanceAPI
from multi_pair_monitor import MultiPairMonitor
from trade_executor import TradeExecutor


def setup_logging() -> logging.Logger:
    """Setup logging configuration.
    
    Returns:
        Configured logger instance
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('trading_bot.log')
        ]
    )
    return logging.getLogger(__name__)


def run_multi_pair_mode(api: BinanceAPI, logger: logging.Logger):
    """Run the bot in multi-pair monitoring mode.
    
    This mode:
    1. Monitors multiple trading pairs for entry signals
    2. Opens trades when signals are found
    3. Continuously monitors open positions
    4. Closes trades when TP or SL levels are hit
    
    Args:
        api: BinanceAPI instance
        logger: Logger instance
    """
    logger.info("Starting Multi-Pair Monitor Mode")
    logger.info(f"Trading Mode: {'DRY RUN' if Config.DRY_RUN else 'LIVE TRADING'}")
    
    # Initialize monitor and executor
    monitor = MultiPairMonitor(api, logger)
    executor = TradeExecutor(api, logger, dry_run=Config.DRY_RUN)
    
    # Start monitoring thread
    monitor.start(update_interval=Config.MONITOR_UPDATE_INTERVAL)
    
    try:
        logger.info("Bot is running. Press Ctrl+C to stop.")
        
        while True:
            # 1. Check for NEW entry signals
            entry_signal = monitor.get_next_entry()
            if entry_signal:
                symbol = entry_signal['symbol']
                data = entry_signal['signal']
                
                logger.info(f"ENTRY SIGNAL FOUND: {symbol}")
                
                # Open the trade
                executor.open_trade(
                    symbol=symbol,
                    entry_price=data['entry_price'],
                    stop_loss=data['stop_loss'],
                    take_profit=data['take_profit'],
                    position_size=data['position_size']
                )
            
            # 2. Monitor ALL open positions for TP/SL
            if executor.open_positions:
                for symbol in list(executor.open_positions.keys()):
                    try:
                        current_price = api.get_current_price(symbol)
                        result = executor.check_positions(symbol, current_price)
                        
                        if result:
                            logger.info(f"Position closed for {symbol}: {result}")
                    except Exception as e:
                        logger.error(f"Error checking position for {symbol}: {e}")
            
            # 3. Wait before next check
            time.sleep(Config.SIGNAL_CHECK_INTERVAL)
            
    except KeyboardInterrupt:
        logger.info("Stopping bot...")
        monitor.stop()
        logger.info("Bot stopped successfully")


def main():
    """Main entry point for the trading bot."""
    logger = setup_logging()
    
    logger.info("=" * 60)
    logger.info("Trading Bot Starting")
    logger.info("=" * 60)
    
    # Initialize Binance API
    api = BinanceAPI(
        api_key=Config.API_KEY,
        api_secret=Config.API_SECRET,
        logger=logger
    )
    
    # Run in multi-pair mode
    run_multi_pair_mode(api, logger)


if __name__ == "__main__":
    main()
