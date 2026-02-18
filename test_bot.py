"""Test script to demonstrate and validate trading bot functionality."""

import logging
import time
import sys
from config import Config
from binance_api import BinanceAPI
from multi_pair_monitor import MultiPairMonitor
from trade_executor import TradeExecutor


def setup_test_logging() -> logging.Logger:
    """Setup logging for test."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    return logging.getLogger(__name__)


def test_trade_execution():
    """Test the complete trade execution flow."""
    logger = setup_test_logging()
    
    logger.info("=" * 60)
    logger.info("Testing Trading Bot - Trade Execution Flow")
    logger.info("=" * 60)
    
    # Initialize components
    api = BinanceAPI(logger=logger)
    monitor = MultiPairMonitor(api, logger)
    executor = TradeExecutor(api, logger, dry_run=True)
    
    # Test 1: Opening a trade
    logger.info("\n[TEST 1] Opening a trade with Take Profit scenario")
    symbol = "BTCUSDT"
    entry_price = 50000.0
    stop_loss = 49000.0
    take_profit = 52000.0
    position_size = 0.1
    
    executor.open_trade(symbol, entry_price, stop_loss, take_profit, position_size)
    
    assert symbol in executor.open_positions, "Trade should be in open positions"
    logger.info("✓ Trade opened successfully")
    
    # Test 2: Check position with price below TP/SL (no action)
    logger.info("\n[TEST 2] Checking position with price at $50,500 (no TP/SL hit)")
    result = executor.check_positions(symbol, 50500.0)
    
    assert result is None, "Position should remain open"
    assert symbol in executor.open_positions, "Trade should still be open"
    logger.info("✓ Position remains open as expected")
    
    # Test 3: Take Profit hit
    logger.info("\n[TEST 3] Take Profit hit at $52,000")
    result = executor.check_positions(symbol, 52000.0)
    
    assert result is not None, "Position should be closed"
    assert result['reason'] == 'TAKE_PROFIT', "Should close due to TP"
    assert symbol not in executor.open_positions, "Trade should be removed from open positions"
    logger.info(f"✓ Trade closed successfully: P&L = ${result['pnl']:.2f}")
    
    # Test 4: Stop Loss scenario
    logger.info("\n[TEST 4] Opening a trade with Stop Loss scenario")
    executor.open_trade(symbol, entry_price, stop_loss, take_profit, position_size)
    
    logger.info("[TEST 4] Stop Loss hit at $49,000")
    result = executor.check_positions(symbol, 49000.0)
    
    assert result is not None, "Position should be closed"
    assert result['reason'] == 'STOP_LOSS', "Should close due to SL"
    logger.info(f"✓ Stop Loss triggered: P&L = ${result['pnl']:.2f}")
    
    # Test 5: Multiple positions
    logger.info("\n[TEST 5] Testing multiple open positions")
    executor.open_trade("BTCUSDT", 50000.0, 49000.0, 52000.0, 0.1)
    executor.open_trade("ETHUSDT", 3000.0, 2900.0, 3200.0, 1.0)
    
    assert len(executor.open_positions) == 2, "Should have 2 open positions"
    logger.info("✓ Multiple positions opened successfully")
    
    # Close all positions
    executor.check_positions("BTCUSDT", 52000.0)
    executor.check_positions("ETHUSDT", 3200.0)
    
    assert len(executor.open_positions) == 0, "All positions should be closed"
    logger.info("✓ All positions closed successfully")
    
    # Test 6: Verify trade history CSV
    logger.info("\n[TEST 6] Checking trade history CSV")
    try:
        with open('trade_history.csv', 'r') as f:
            lines = f.readlines()
            assert len(lines) > 1, "Trade history should have entries"
            logger.info(f"✓ Trade history contains {len(lines) - 1} trades")
            logger.info("Sample entries:")
            for line in lines[:5]:  # Show first 5 lines
                logger.info(f"  {line.strip()}")
    except FileNotFoundError:
        logger.error("✗ Trade history file not found")
        return False
    
    logger.info("\n" + "=" * 60)
    logger.info("All tests passed! ✓")
    logger.info("=" * 60)
    
    return True


def test_monitor_integration():
    """Test the monitor and executor integration."""
    logger = setup_test_logging()
    
    logger.info("\n" + "=" * 60)
    logger.info("Testing Monitor + Executor Integration")
    logger.info("=" * 60)
    
    # Initialize components
    api = BinanceAPI(logger=logger)
    monitor = MultiPairMonitor(api, logger)
    executor = TradeExecutor(api, logger, dry_run=True)
    
    # Add some test signals
    logger.info("\n[TEST] Adding entry signals to monitor queue")
    monitor.add_entry_signal("BTCUSDT", 50000.0, 49000.0, 52000.0, 0.1)
    monitor.add_entry_signal("ETHUSDT", 3000.0, 2900.0, 3200.0, 1.0)
    
    # Simulate main loop
    logger.info("\n[TEST] Simulating main loop - processing signals")
    
    iteration = 0
    max_iterations = 5
    
    while iteration < max_iterations:
        # Check for entry signals
        entry_signal = monitor.get_next_entry()
        if entry_signal:
            symbol = entry_signal['symbol']
            data = entry_signal['signal']
            
            logger.info(f"Processing entry signal for {symbol}")
            executor.open_trade(
                symbol=symbol,
                entry_price=data['entry_price'],
                stop_loss=data['stop_loss'],
                take_profit=data['take_profit'],
                position_size=data['position_size']
            )
        
        # Monitor open positions
        for symbol in list(executor.open_positions.keys()):
            # Simulate price reaching TP
            pos = executor.open_positions[symbol]
            simulated_price = pos['take_profit']
            
            result = executor.check_positions(symbol, simulated_price)
            if result:
                logger.info(f"Position closed: {result}")
        
        iteration += 1
        time.sleep(0.5)
    
    logger.info("\n✓ Integration test completed successfully")
    
    return True


if __name__ == "__main__":
    success = True
    
    # Run tests
    success = test_trade_execution() and success
    success = test_monitor_integration() and success
    
    if success:
        print("\n✓ All tests passed!")
        sys.exit(0)
    else:
        print("\n✗ Some tests failed")
        sys.exit(1)
