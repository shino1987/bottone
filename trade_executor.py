"""Trade execution and monitoring system."""

import logging
from datetime import datetime
from typing import Dict, Optional
from binance_api import BinanceAPI


class TradeExecutor:
    """Handles opening, closing, and monitoring trades."""
    
    def __init__(self, api: BinanceAPI, logger: logging.Logger, dry_run: bool = True):
        """Initialize trade executor.
        
        Args:
            api: BinanceAPI instance
            logger: Logger instance
            dry_run: If True, simulates trades without executing them
        """
        self.api = api
        self.logger = logger
        self.dry_run = dry_run
        self.open_positions = {}
        
        # Initialize trade history CSV file with headers if it doesn't exist
        try:
            with open('trade_history.csv', 'x') as f:
                f.write("symbol,entry_price,exit_price,reason,pnl,entry_time,exit_time\n")
        except FileExistsError:
            pass
    
    def open_trade(self, symbol: str, entry_price: float, stop_loss: float, 
                   take_profit: float, position_size: float):
        """Open a new trade.
        
        Args:
            symbol: Trading pair symbol
            entry_price: Entry price level
            stop_loss: Stop loss price level
            take_profit: Take profit price level
            position_size: Position size
        """
        if self.dry_run:
            # Simulate trade opening
            self.open_positions[symbol] = {
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'position_size': position_size,
                'entry_time': datetime.now(),
                'status': 'OPEN'
            }
            self.logger.info(f"[DRY RUN] TRADE OPENED: {symbol} @ ${entry_price:.2f}")
            self.logger.info(f"[DRY RUN] Stop Loss: ${stop_loss:.2f} | Take Profit: ${take_profit:.2f}")
        else:
            # Execute real trade on Binance
            order = self.api.place_order(symbol, 'BUY', position_size, entry_price)
            self.open_positions[symbol] = {
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'position_size': position_size,
                'entry_time': datetime.now(),
                'order_id': order['orderId'],
                'status': 'OPEN'
            }
            self.logger.info(f"TRADE OPENED: {symbol} @ ${entry_price:.2f} - Order ID: {order['orderId']}")
            self.logger.info(f"Stop Loss: ${stop_loss:.2f} | Take Profit: ${take_profit:.2f}")
    
    def check_positions(self, symbol: str, current_price: float) -> Optional[Dict]:
        """Check if Take Profit or Stop Loss is hit for a position.
        
        Args:
            symbol: Trading pair symbol
            current_price: Current market price
            
        Returns:
            Trade result dictionary if position was closed, None otherwise
        """
        if symbol not in self.open_positions:
            return None
        
        pos = self.open_positions[symbol]
        
        # Take Profit hit
        if current_price >= pos['take_profit']:
            return self.close_trade(symbol, current_price, 'TAKE_PROFIT')
        
        # Stop Loss hit
        if current_price <= pos['stop_loss']:
            return self.close_trade(symbol, current_price, 'STOP_LOSS')
        
        return None
    
    def close_trade(self, symbol: str, exit_price: float, reason: str) -> Optional[Dict]:
        """Close a trade.
        
        Args:
            symbol: Trading pair symbol
            exit_price: Exit price level
            reason: Reason for closing (e.g., 'TAKE_PROFIT', 'STOP_LOSS')
            
        Returns:
            Trade result dictionary
        """
        if symbol not in self.open_positions:
            return None
        
        pos = self.open_positions[symbol]
        pnl = (exit_price - pos['entry_price']) * pos['position_size']
        exit_time = datetime.now()
        
        if self.dry_run:
            self.logger.info(f"[DRY RUN] TRADE CLOSED: {symbol} @ ${exit_price:.2f} - {reason}")
            self.logger.info(f"[DRY RUN] P&L: ${pnl:.2f}")
        else:
            # Execute close order on Binance
            order = self.api.place_order(symbol, 'SELL', pos['position_size'], exit_price)
            self.logger.info(f"TRADE CLOSED: {symbol} @ ${exit_price:.2f} - {reason}")
            self.logger.info(f"P&L: ${pnl:.2f}")
        
        # Log trade result
        self._log_trade(symbol, pos, exit_price, reason, pnl, exit_time)
        
        # Remove from open positions
        del self.open_positions[symbol]
        
        return {
            'symbol': symbol,
            'entry': pos['entry_price'],
            'exit': exit_price,
            'reason': reason,
            'pnl': pnl
        }
    
    def _log_trade(self, symbol: str, position: Dict, exit_price: float, 
                   reason: str, pnl: float, exit_time: datetime):
        """Log trade to CSV file.
        
        Args:
            symbol: Trading pair symbol
            position: Position dictionary
            exit_price: Exit price level
            reason: Closing reason
            pnl: Profit and loss amount
            exit_time: Exit timestamp
        """
        try:
            with open('trade_history.csv', 'a') as f:
                entry_time_str = position['entry_time'].strftime('%Y-%m-%d %H:%M:%S')
                exit_time_str = exit_time.strftime('%Y-%m-%d %H:%M:%S')
                f.write(f"{symbol},{position['entry_price']:.2f},{exit_price:.2f},"
                       f"{reason},{pnl:.2f},{entry_time_str},{exit_time_str}\n")
        except Exception as e:
            self.logger.error(f"Error logging trade to CSV: {e}")
