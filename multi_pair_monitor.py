"""
Multi-Pair Monitor for 7-Step Trading Strategy
Monitors multiple trading pairs in parallel using threading.
"""

import logging
import threading
import time
from typing import Dict, List, Optional, Any
from datetime import datetime
from queue import Queue

from binance_api import BinanceAPI
from filters.state_machine import TradingStateMachine, TradingState


class PairMonitor:
    """Monitor for a single trading pair."""
    
    def __init__(self, symbol: str, api: BinanceAPI):
        """
        Initialize pair monitor.
        
        Args:
            symbol: Trading pair symbol
            api: BinanceAPI instance
        """
        self.symbol = symbol
        self.api = api
        self.state_machine = TradingStateMachine()
        self.logger = logging.getLogger(f"{__name__}.{symbol}")
        
        # Statistics
        self.stats = {
            'symbol': symbol,
            'current_state': 'IDLE',
            'signals_found': 0,
            'last_update': None,
            'errors': 0,
        }
        
    def update(self) -> Optional[Dict[str, Any]]:
        """
        Update the monitor with latest data.
        
        Returns:
            Entry signal if found, None otherwise
        """
        try:
            # Get historical candles
            candles = self._get_candles()
            if not candles:
                self.stats['errors'] += 1
                return None
            
            # Prepare market data
            market_data = {
                'symbol': self.symbol,
                'candles': candles,
                'timestamp': datetime.now().isoformat(),
            }
            
            # Process through state machine
            status = self.state_machine.process(market_data)
            
            # Update statistics
            self.stats['current_state'] = status['state']
            self.stats['last_update'] = datetime.now().isoformat()
            
            # Check for entry signal
            if status['entry_signal']:
                self.stats['signals_found'] += 1
                self.logger.info(f"Entry signal found for {self.symbol}")
                return {
                    'symbol': self.symbol,
                    'signal': status['entry_signal'],
                    'timestamp': datetime.now().isoformat(),
                }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error updating {self.symbol}: {e}", exc_info=True)
            self.stats['errors'] += 1
            return None
    
    def _get_candles(self) -> Optional[List[Dict[str, Any]]]:
        """
        Get historical candles for the pair.
        
        Returns:
            List of candle dictionaries or None
        """
        try:
            # Get klines from Binance (15m timeframe, 50 candles)
            klines = self.api.client.get_klines(
                symbol=self.symbol,
                interval='15m',
                limit=50
            )
            
            # Convert to candle format
            candles = []
            for kline in klines:
                candle = {
                    'timestamp': kline[0],
                    'open': float(kline[1]),
                    'high': float(kline[2]),
                    'low': float(kline[3]),
                    'close': float(kline[4]),
                    'volume': float(kline[5]),
                }
                candles.append(candle)
            
            return candles
            
        except Exception as e:
            self.logger.error(f"Error getting candles for {self.symbol}: {e}")
            return None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get monitor statistics."""
        return self.stats
    
    def reset(self):
        """Reset monitor state."""
        self.state_machine.reset()


class MultiPairMonitor:
    """
    Multi-Pair Monitor with Threading
    - Monitor 20 USDC pairs in parallel
    - Each pair maintains independent state
    - Threading for parallel monitoring
    - Real-time statistics per pair
    - Queue of entry points found
    """
    
    # Default pairs to monitor
    DEFAULT_PAIRS = [
        'BTCUSDC', 'ETHUSDC', 'SOLUSDC', 'BNBUSDC', 'ADAUSDC',
        'XRPUSDC', 'DOGEUSDC', 'LTCUSDC', 'MATICUSDC', 'AVAXUSDC',
        'UNIUSDC', 'LINKUSDC', 'ARBUSDC', 'OPUSDC', 'FTMUSDC',
        'ONEUSDC', 'APTUSDC', 'SUIUSDC', 'PEPEUSDC', 'GALEUSDC',
    ]
    
    def __init__(self, api: BinanceAPI, pairs: Optional[List[str]] = None):
        """
        Initialize multi-pair monitor.
        
        Args:
            api: BinanceAPI instance
            pairs: List of trading pairs to monitor (default: DEFAULT_PAIRS)
        """
        self.logger = logging.getLogger(__name__)
        self.api = api
        self.pairs = pairs or self.DEFAULT_PAIRS
        
        # Create monitors for each pair
        self.monitors: Dict[str, PairMonitor] = {}
        for symbol in self.pairs:
            self.monitors[symbol] = PairMonitor(symbol, api)
        
        # Entry signals queue
        self.entry_queue: Queue = Queue()
        
        # Control flags
        self.running = False
        self.threads: List[threading.Thread] = []
        
        # Statistics
        self.global_stats = {
            'started_at': None,
            'total_signals': 0,
            'active_pairs': len(self.pairs),
        }
        
        self.logger.info(f"Multi-pair monitor initialized with {len(self.pairs)} pairs")
    
    def start(self, update_interval: int = 60):
        """
        Start monitoring all pairs.
        
        Args:
            update_interval: Update interval in seconds (default: 60)
        """
        if self.running:
            self.logger.warning("Monitor already running")
            return
        
        self.running = True
        self.global_stats['started_at'] = datetime.now().isoformat()
        
        self.logger.info(f"Starting multi-pair monitor (interval: {update_interval}s)")
        
        # Create and start threads for each pair
        for symbol, monitor in self.monitors.items():
            thread = threading.Thread(
                target=self._monitor_pair,
                args=(symbol, monitor, update_interval),
                daemon=True,
                name=f"Monitor-{symbol}"
            )
            thread.start()
            self.threads.append(thread)
        
        self.logger.info(f"Started {len(self.threads)} monitor threads")
    
    def _monitor_pair(self, symbol: str, monitor: PairMonitor, interval: int):
        """
        Monitor a single pair in a thread.
        
        Args:
            symbol: Trading pair symbol
            monitor: PairMonitor instance
            interval: Update interval in seconds
        """
        self.logger.info(f"Started monitoring {symbol}")
        
        while self.running:
            try:
                # Update monitor
                signal = monitor.update()
                
                # If entry signal found, add to queue
                if signal:
                    self.entry_queue.put(signal)
                    self.global_stats['total_signals'] += 1
                    self.logger.info(f"Entry signal added to queue: {symbol}")
                
                # Sleep until next update
                time.sleep(interval)
                
            except Exception as e:
                self.logger.error(f"Error in {symbol} monitor thread: {e}", exc_info=True)
                time.sleep(interval)
    
    def stop(self):
        """Stop monitoring all pairs."""
        if not self.running:
            return
        
        self.logger.info("Stopping multi-pair monitor...")
        self.running = False
        
        # Wait for threads to finish
        for thread in self.threads:
            thread.join(timeout=5)
        
        self.threads.clear()
        self.logger.info("Multi-pair monitor stopped")
    
    def get_next_entry(self) -> Optional[Dict[str, Any]]:
        """
        Get next entry signal from queue.
        
        Returns:
            Entry signal dictionary or None if queue is empty
        """
        if not self.entry_queue.empty():
            return self.entry_queue.get()
        return None
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics for all monitored pairs.
        
        Returns:
            Dictionary with global and per-pair statistics
        """
        pair_stats = {}
        for symbol, monitor in self.monitors.items():
            pair_stats[symbol] = monitor.get_stats()
        
        return {
            'global': self.global_stats,
            'pairs': pair_stats,
            'queue_size': self.entry_queue.qsize(),
        }
    
    def print_statistics(self):
        """Print statistics to console."""
        stats = self.get_statistics()
        
        print("\n" + "=" * 80)
        print("MULTI-PAIR MONITOR STATISTICS")
        print("=" * 80)
        print(f"Started at: {stats['global']['started_at']}")
        print(f"Active pairs: {stats['global']['active_pairs']}")
        print(f"Total signals found: {stats['global']['total_signals']}")
        print(f"Entry queue size: {stats['queue_size']}")
        print("\nPer-Pair Status:")
        print("-" * 80)
        
        for symbol, pair_stats in sorted(stats['pairs'].items()):
            print(f"{symbol:12} | State: {pair_stats['current_state']:20} | "
                  f"Signals: {pair_stats['signals_found']:3} | "
                  f"Errors: {pair_stats['errors']:3}")
        
        print("=" * 80 + "\n")
    
    def is_running(self) -> bool:
        """Check if monitor is running."""
        return self.running
    
    def get_pair_status(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get status for a specific pair.
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            Pair statistics or None if not found
        """
        if symbol in self.monitors:
            return self.monitors[symbol].get_stats()
        return None
