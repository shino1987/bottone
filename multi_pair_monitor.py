"""
Multi-pair monitor for trading bot.
Monitors 20 USDC pairs in parallel.
"""

import logging
import time
import threading
from typing import Dict, List, Optional, Any
from queue import Queue
from datetime import datetime

from binance_api import BinanceAPI
from filters.state_machine import StateMachine, TradingState


class MultiPairMonitor:
    """
    Monitor multiple trading pairs in parallel.
    
    Each pair maintains independent state machine.
    Uses threading for parallel monitoring.
    """
    
    def __init__(
        self,
        api: BinanceAPI,
        trading_pairs: List[str],
        interval: str = '15m',
        kline_limit: int = 50,
        check_interval: int = 60
    ):
        """
        Initialize multi-pair monitor.
        
        Args:
            api: BinanceAPI instance
            trading_pairs: List of trading pair symbols
            interval: Candlestick interval (default: '15m')
            kline_limit: Number of candles to fetch (default: 50)
            check_interval: Seconds between checks (default: 60)
        """
        self.logger = logging.getLogger(__name__)
        self.api = api
        self.trading_pairs = trading_pairs
        self.interval = interval
        self.kline_limit = kline_limit
        self.check_interval = check_interval
        
        # State machine for each pair
        self.state_machines: Dict[str, StateMachine] = {}
        for symbol in trading_pairs:
            self.state_machines[symbol] = StateMachine(symbol)
        
        # Entry queue
        self.entry_queue = Queue()
        
        # Statistics
        self.stats = {
            symbol: {
                'checks': 0,
                'errors': 0,
                'last_check': None,
                'state': TradingState.IDLE.value
            }
            for symbol in trading_pairs
        }
        
        # Control flags
        self.running = False
        self.threads: List[threading.Thread] = []
        
        self.logger.info(f"Multi-pair monitor initialized with {len(trading_pairs)} pairs")
    
    def _monitor_pair(self, symbol: str):
        """
        Monitor a single trading pair.
        
        Args:
            symbol: Trading pair symbol
        """
        self.logger.info(f"Starting monitoring for {symbol}")
        state_machine = self.state_machines[symbol]
        
        while self.running:
            try:
                # Get market data
                klines = self.api.get_klines(symbol, self.interval, self.kline_limit)
                
                if not klines:
                    self.logger.warning(f"{symbol}: Failed to get klines")
                    self.stats[symbol]['errors'] += 1
                    time.sleep(self.check_interval)
                    continue
                
                price = self.api.get_symbol_price(symbol)
                if not price:
                    self.logger.warning(f"{symbol}: Failed to get price")
                    self.stats[symbol]['errors'] += 1
                    time.sleep(self.check_interval)
                    continue
                
                # Prepare market data
                market_data = {
                    'symbol': symbol,
                    'klines': klines,
                    'price': price,
                    'timestamp': datetime.now().isoformat()
                }
                
                # Update state machine
                entry_details = state_machine.update(market_data)
                
                # Update stats
                self.stats[symbol]['checks'] += 1
                self.stats[symbol]['last_check'] = datetime.now().isoformat()
                self.stats[symbol]['state'] = state_machine.get_state().value
                
                # If entry triggered, add to queue
                if entry_details:
                    entry_data = {
                        'symbol': symbol,
                        'entry': entry_details['entry'],
                        'stop_loss': entry_details['stop_loss'],
                        'take_profit': entry_details['take_profit'],
                        'risk_reward': entry_details['risk_reward'],
                        'timestamp': datetime.now().isoformat()
                    }
                    self.entry_queue.put(entry_data)
                    self.logger.info(f"Entry added to queue: {symbol} @ {entry_details['entry']:.2f}")
                
                # Log state periodically
                if self.stats[symbol]['checks'] % 10 == 0:
                    self.logger.debug(
                        f"{symbol}: State={state_machine.get_state().value}, "
                        f"Checks={self.stats[symbol]['checks']}, "
                        f"Errors={self.stats[symbol]['errors']}"
                    )
                
                time.sleep(self.check_interval)
                
            except Exception as e:
                self.logger.error(f"{symbol}: Error in monitoring loop: {e}", exc_info=True)
                self.stats[symbol]['errors'] += 1
                time.sleep(self.check_interval)
        
        self.logger.info(f"Stopped monitoring for {symbol}")
    
    def start(self):
        """Start monitoring all pairs."""
        if self.running:
            self.logger.warning("Monitor already running")
            return
        
        self.running = True
        self.logger.info(f"Starting multi-pair monitor for {len(self.trading_pairs)} pairs")
        
        # Start thread for each pair
        for symbol in self.trading_pairs:
            thread = threading.Thread(
                target=self._monitor_pair,
                args=(symbol,),
                name=f"Monitor-{symbol}",
                daemon=True
            )
            thread.start()
            self.threads.append(thread)
            self.logger.info(f"Started thread for {symbol}")
        
        self.logger.info("All monitoring threads started")
    
    def stop(self):
        """Stop monitoring all pairs."""
        if not self.running:
            self.logger.warning("Monitor not running")
            return
        
        self.logger.info("Stopping multi-pair monitor...")
        self.running = False
        
        # Wait for all threads to finish
        for thread in self.threads:
            thread.join(timeout=5)
        
        self.threads.clear()
        self.logger.info("Multi-pair monitor stopped")
    
    def get_entry_queue(self) -> Queue:
        """Get the entry queue."""
        return self.entry_queue
    
    def get_next_entry(self) -> Optional[Dict[str, Any]]:
        """
        Get next entry from queue.
        
        Returns:
            Entry data or None if queue is empty
        """
        if self.entry_queue.empty():
            return None
        
        return self.entry_queue.get()
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get monitoring statistics.
        
        Returns:
            Dictionary with statistics for all pairs
        """
        return {
            'pairs': len(self.trading_pairs),
            'running': self.running,
            'entry_queue_size': self.entry_queue.qsize(),
            'pair_stats': self.stats.copy()
        }
    
    def get_dashboard_data(self) -> str:
        """
        Get formatted dashboard data.
        
        Returns:
            Formatted string with dashboard data
        """
        lines = [
            "=" * 80,
            f"Multi-Pair Monitor Dashboard - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "=" * 80,
            f"Status: {'RUNNING' if self.running else 'STOPPED'}",
            f"Monitored Pairs: {len(self.trading_pairs)}",
            f"Entry Queue: {self.entry_queue.qsize()} entries",
            "-" * 80,
            f"{'Symbol':<15} {'State':<20} {'Checks':<10} {'Errors':<10} {'Last Check'}",
            "-" * 80
        ]
        
        for symbol in sorted(self.trading_pairs):
            stats = self.stats[symbol]
            last_check = stats['last_check'] or 'Never'
            if stats['last_check']:
                # Format timestamp
                try:
                    dt = datetime.fromisoformat(stats['last_check'])
                    last_check = dt.strftime('%H:%M:%S')
                except (ValueError, TypeError):
                    pass
            
            lines.append(
                f"{symbol:<15} {stats['state']:<20} {stats['checks']:<10} "
                f"{stats['errors']:<10} {last_check}"
            )
        
        lines.append("=" * 80)
        
        return "\n".join(lines)
    
    def reset_pair_state(self, symbol: str):
        """
        Reset state machine for a specific pair.
        
        Args:
            symbol: Trading pair symbol
        """
        if symbol in self.state_machines:
            self.state_machines[symbol].reset_after_trade()
            self.logger.info(f"Reset state machine for {symbol}")
        else:
            self.logger.warning(f"Symbol {symbol} not found in state machines")
