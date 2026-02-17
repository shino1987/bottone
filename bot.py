"""
Main trading bot logic with risk management and order execution.
"""

import logging
import time
from typing import List, Optional, Dict, Any
from datetime import datetime

from config import Config
from binance_api import BinanceAPI
from filters.base_filter import BaseFilter
from filters.state_machine import TradingStateMachine


class TradingBot:
    """
    Main trading bot class that manages orders, positions, and risk.
    """

    def __init__(
        self,
        api: BinanceAPI,
        filters: Optional[List[BaseFilter]] = None,
        symbols: Optional[List[str]] = None
    ):
        """
        Initialize the trading bot.
        
        Args:
            api: BinanceAPI instance
            filters: List of trading filters to apply
            symbols: List of trading pair symbols (for multi-pair support)
        """
        self.logger = logging.getLogger(__name__)
        self.api = api
        self.filters = filters or []
        
        # Multi-pair support
        self.symbols = symbols or [Config.TRADING_PAIR]
        self.state_machines: Dict[str, TradingStateMachine] = {}
        
        # Initialize state machine for each symbol
        for symbol in self.symbols:
            self.state_machines[symbol] = TradingStateMachine(symbol)
        
        # Default single symbol for backwards compatibility
        self.symbol = self.symbols[0] if self.symbols else Config.TRADING_PAIR
        
        self.leverage = Config.LEVERAGE
        self.position_size = Config.POSITION_SIZE
        self.stop_loss_percent = Config.STOP_LOSS_PERCENT
        self.take_profit_percent = Config.TAKE_PROFIT_PERCENT
        self.dry_run = Config.DRY_RUN
        
        # Per-symbol position tracking
        self.positions: Dict[str, Optional[Dict[str, Any]]] = {symbol: None for symbol in self.symbols}
        self.entry_prices: Dict[str, Optional[float]] = {symbol: None for symbol in self.symbols}
        self.stop_loss_prices: Dict[str, Optional[float]] = {symbol: None for symbol in self.symbols}
        self.take_profit_prices: Dict[str, Optional[float]] = {symbol: None for symbol in self.symbols}
        
        # Legacy single position fields for backwards compatibility
        self.current_position: Optional[Dict[str, Any]] = None
        self.entry_price: Optional[float] = None
        self.stop_loss_price: Optional[float] = None
        self.take_profit_price: Optional[float] = None
        
        self.logger.info("TradingBot initialized")
        self.logger.info(f"Trading pairs: {len(self.symbols)}")
        self.logger.info(f"Filters loaded: {len(self.filters)}")

    def add_filter(self, filter_instance: BaseFilter) -> None:
        """
        Add a filter to the bot.
        
        Args:
            filter_instance: Filter instance to add
        """
        self.filters.append(filter_instance)
        self.logger.info(f"Filter added: {filter_instance.name}")

    def get_state_machine(self, symbol: Optional[str] = None) -> TradingStateMachine:
        """
        Get the state machine for a symbol.
        
        Args:
            symbol: Trading pair symbol (defaults to primary symbol)
            
        Returns:
            TradingStateMachine instance for the symbol
        """
        if symbol is None:
            symbol = self.symbol
        return self.state_machines.get(symbol)
    
    def get_current_state(self, symbol: Optional[str] = None) -> int:
        """
        Get the current state for a symbol.
        
        Args:
            symbol: Trading pair symbol (defaults to primary symbol)
            
        Returns:
            Current state number
        """
        state_machine = self.get_state_machine(symbol)
        return state_machine.get_current_state() if state_machine else 0
    
    def transition_state(
        self,
        new_state: int,
        symbol: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Transition to a new state for a symbol.
        
        Args:
            new_state: Target state number
            symbol: Trading pair symbol (defaults to primary symbol)
            data: Optional data associated with the transition
            
        Returns:
            True if transition was successful, False otherwise
        """
        state_machine = self.get_state_machine(symbol)
        if not state_machine:
            self.logger.error(f"No state machine found for {symbol}")
            return False
        
        return state_machine.transition_to(new_state, data)
    
    def get_market_data_with_ohlcv(self, symbol: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get market data including OHLCV for a symbol.
        
        Args:
            symbol: Trading pair symbol (defaults to primary symbol)
            
        Returns:
            Dictionary with market data including OHLCV or None on error
        """
        if symbol is None:
            symbol = self.symbol
        
        price = self.api.get_symbol_price(symbol)
        if price is None:
            return None
        
        # Fetch 15-minute OHLCV data (last 50 candles)
        ohlcv = self.api.get_ohlcv(symbol, interval='15m', limit=50)
        if ohlcv is None:
            self.logger.warning(f"Could not fetch OHLCV data for {symbol}")
            # Return basic data without OHLCV
            return {
                'symbol': symbol,
                'price': price,
                'timestamp': datetime.now().isoformat()
            }
        
        return {
            'symbol': symbol,
            'price': price,
            'ohlcv': ohlcv,
            'timestamp': datetime.now().isoformat()
        }

    def get_market_data(self) -> Optional[Dict[str, Any]]:
        """
        Get current market data for the trading symbol.
        
        Returns:
            Dictionary with market data or None on error
        """
        price = self.api.get_symbol_price(self.symbol)
        if price is None:
            return None
        
        return {
            'symbol': self.symbol,
            'price': price,
            'timestamp': datetime.now().isoformat()
        }

    def apply_filters(self, market_data: Dict[str, Any]) -> str:
        """
        Apply all filters to market data and get consensus signal.
        
        Args:
            market_data: Market data dictionary
            
        Returns:
            Trading signal: 'BUY', 'SELL', or 'HOLD'
        """
        if not self.filters:
            self.logger.warning("No filters configured, returning HOLD")
            return 'HOLD'
        
        signals = []
        for filter_instance in self.filters:
            signal = filter_instance.get_signal(market_data)
            signals.append(signal)
            self.logger.debug(f"Filter {filter_instance.name} signal: {signal}")
        
        # Simple consensus: all filters must agree for BUY/SELL
        if all(s == 'BUY' for s in signals):
            return 'BUY'
        elif all(s == 'SELL' for s in signals):
            return 'SELL'
        else:
            return 'HOLD'

    def calculate_stop_loss(self, entry_price: float, side: str) -> float:
        """
        Calculate stop loss price based on entry price and configured percentage.
        
        Args:
            entry_price: Entry price of the position
            side: 'BUY' or 'SELL'
            
        Returns:
            Stop loss price
        """
        if side == 'BUY':
            # For long position, stop loss is below entry
            return entry_price * (1 - self.stop_loss_percent / 100)
        else:
            # For short position, stop loss is above entry
            return entry_price * (1 + self.stop_loss_percent / 100)

    def calculate_take_profit(self, entry_price: float, side: str) -> float:
        """
        Calculate take profit price based on entry price and configured percentage.
        
        Args:
            entry_price: Entry price of the position
            side: 'BUY' or 'SELL'
            
        Returns:
            Take profit price
        """
        if side == 'BUY':
            # For long position, take profit is above entry
            return entry_price * (1 + self.take_profit_percent / 100)
        else:
            # For short position, take profit is below entry
            return entry_price * (1 - self.take_profit_percent / 100)

    def open_position(self, side: str, price: float) -> bool:
        """
        Open a new position.
        
        Args:
            side: 'BUY' or 'SELL'
            price: Current market price
            
        Returns:
            True if position opened successfully, False otherwise
        """
        if self.current_position:
            self.logger.warning("Position already open, cannot open new position")
            return False
        
        # Calculate quantity based on position size
        # Note: In production, this should be rounded according to the symbol's
        # LOT_SIZE filter from exchange info to meet Binance's trading rules
        quantity = self.position_size / price
        
        if self.dry_run:
            self.logger.info(f"[DRY RUN] Would open {side} position: {quantity} @ {price}")
            self.current_position = {
                'side': side,
                'quantity': quantity,
                'entry_price': price
            }
        else:
            order = self.api.create_margin_order(
                symbol=self.symbol,
                side=side,
                order_type='MARKET',
                quantity=quantity
            )
            
            if not order:
                self.logger.error("Failed to create order")
                return False
            
            self.current_position = {
                'side': side,
                'quantity': quantity,
                'entry_price': price,
                'order': order
            }
        
        self.entry_price = price
        self.stop_loss_price = self.calculate_stop_loss(price, side)
        self.take_profit_price = self.calculate_take_profit(price, side)
        
        self.logger.info(f"Position opened: {side} {quantity} @ {price}")
        self.logger.info(f"Stop Loss: {self.stop_loss_price:.2f}")
        self.logger.info(f"Take Profit: {self.take_profit_price:.2f}")
        
        return True

    def close_position(self, reason: str = "Manual close") -> bool:
        """
        Close the current position.
        
        Args:
            reason: Reason for closing the position
            
        Returns:
            True if position closed successfully, False otherwise
        """
        if not self.current_position:
            self.logger.warning("No position to close")
            return False
        
        side = self.current_position['side']
        quantity = self.current_position['quantity']
        
        # Reverse the side to close position
        close_side = 'SELL' if side == 'BUY' else 'BUY'
        
        if self.dry_run:
            self.logger.info(f"[DRY RUN] Would close position: {close_side} {quantity}")
        else:
            order = self.api.create_margin_order(
                symbol=self.symbol,
                side=close_side,
                order_type='MARKET',
                quantity=quantity
            )
            
            if not order:
                self.logger.error("Failed to close position")
                return False
        
        self.logger.info(f"Position closed: {reason}")
        self.current_position = None
        self.entry_price = None
        self.stop_loss_price = None
        self.take_profit_price = None
        
        return True

    def check_stop_loss_take_profit(self, current_price: float) -> None:
        """
        Check if stop loss or take profit has been hit.
        
        Args:
            current_price: Current market price
        """
        if not self.current_position:
            return
        
        side = self.current_position['side']
        
        if side == 'BUY':
            # Long position
            if current_price <= self.stop_loss_price:
                self.logger.warning(f"Stop Loss hit at {current_price}")
                self.close_position("Stop Loss")
            elif current_price >= self.take_profit_price:
                self.logger.info(f"Take Profit hit at {current_price}")
                self.close_position("Take Profit")
        else:
            # Short position
            if current_price >= self.stop_loss_price:
                self.logger.warning(f"Stop Loss hit at {current_price}")
                self.close_position("Stop Loss")
            elif current_price <= self.take_profit_price:
                self.logger.info(f"Take Profit hit at {current_price}")
                self.close_position("Take Profit")

    def run_iteration(self) -> None:
        """
        Run a single iteration of the bot logic.
        """
        # Get market data
        market_data = self.get_market_data()
        if not market_data:
            self.logger.error("Failed to get market data")
            return
        
        current_price = market_data['price']
        self.logger.info(f"Current price for {self.symbol}: {current_price}")
        
        # Check stop loss / take profit if position is open
        if self.current_position:
            self.check_stop_loss_take_profit(current_price)
            return
        
        # Apply filters to get signal
        signal = self.apply_filters(market_data)
        self.logger.info(f"Trading signal: {signal}")
        
        # Execute based on signal
        if signal == 'BUY' and not self.current_position:
            self.open_position('BUY', current_price)
        elif signal == 'SELL' and not self.current_position:
            self.open_position('SELL', current_price)

    def run(self, iterations: Optional[int] = None, interval: int = 60) -> None:
        """
        Run the bot continuously or for a specified number of iterations.
        
        Args:
            iterations: Number of iterations to run (None for infinite)
            interval: Time interval between iterations in seconds
        """
        self.logger.info("Starting trading bot...")
        
        iteration_count = 0
        try:
            while True:
                self.run_iteration()
                
                iteration_count += 1
                if iterations and iteration_count >= iterations:
                    self.logger.info(f"Completed {iterations} iterations, stopping")
                    break
                
                self.logger.debug(f"Waiting {interval} seconds until next iteration")
                time.sleep(interval)
                
        except KeyboardInterrupt:
            self.logger.info("Bot stopped by user")
        except Exception as e:
            self.logger.error(f"Bot error: {e}", exc_info=True)
        finally:
            if self.current_position:
                self.logger.info("Closing open position before shutdown")
                self.close_position("Bot shutdown")

    def get_status(self) -> Dict[str, Any]:
        """
        Get current bot status.
        
        Returns:
            Dictionary with bot status information
        """
        # Get state information for all symbols
        states_info = {}
        for symbol in self.symbols:
            state_machine = self.get_state_machine(symbol)
            if state_machine:
                states_info[symbol] = state_machine.get_status()
        
        return {
            'symbol': self.symbol,
            'symbols': self.symbols,
            'leverage': self.leverage,
            'dry_run': self.dry_run,
            'has_position': self.current_position is not None,
            'position': self.current_position,
            'entry_price': self.entry_price,
            'stop_loss': self.stop_loss_price,
            'take_profit': self.take_profit_price,
            'filters_count': len(self.filters),
            'states': states_info,
            'positions_per_symbol': {
                symbol: {
                    'has_position': self.positions[symbol] is not None,
                    'entry_price': self.entry_prices[symbol]
                }
                for symbol in self.symbols
            }
        }
