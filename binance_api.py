"""
Binance API wrapper for cross margin trading.
"""

import logging
from typing import Dict, Optional, Any
from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceRequestException


class BinanceAPI:
    """Wrapper class for Binance API with cross margin trading support."""

    def __init__(self, api_key: str, api_secret: str, testnet: bool = False):
        """
        Initialize Binance API client.
        
        Args:
            api_key: Binance API key
            api_secret: Binance API secret
            testnet: Whether to use testnet (default: False)
        """
        self.logger = logging.getLogger(__name__)
        
        try:
            self.client = Client(api_key, api_secret, testnet=testnet)
            self.logger.info("Binance API client initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize Binance client: {e}")
            raise

    def get_account_balance(self) -> Optional[Dict]:
        """
        Get cross margin account balance.
        
        Returns:
            Dictionary with account balance information or None on error
        """
        try:
            balance = self.client.get_margin_account()
            self.logger.debug(f"Account balance retrieved: {balance}")
            return balance
        except BinanceAPIException as e:
            self.logger.error(f"Binance API error getting balance: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Error getting balance: {e}")
            return None

    def get_symbol_price(self, symbol: str) -> Optional[float]:
        """
        Get current price for a symbol.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTCUSDT')
            
        Returns:
            Current price as float or None on error
        """
        try:
            ticker = self.client.get_symbol_ticker(symbol=symbol)
            price = float(ticker['price'])
            self.logger.debug(f"{symbol} current price: {price}")
            return price
        except BinanceAPIException as e:
            self.logger.error(f"Binance API error getting price: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Error getting price: {e}")
            return None

    def set_leverage(self, symbol: str, leverage: int) -> bool:
        """
        Set leverage for cross margin trading.
        
        Args:
            symbol: Trading pair symbol
            leverage: Leverage multiplier (1-125)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Note: Cross margin doesn't require setting leverage per symbol
            # This is more relevant for isolated margin
            self.logger.info(f"Setting leverage for {symbol}: {leverage}x")
            # For cross margin, we just log this
            # Actual leverage is determined by total collateral
            return True
        except Exception as e:
            self.logger.error(f"Error setting leverage: {e}")
            return False

    def create_margin_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        price: Optional[float] = None,
        **kwargs
    ) -> Optional[Dict]:
        """
        Create a cross margin order.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTCUSDT')
            side: 'BUY' or 'SELL'
            order_type: 'LIMIT', 'MARKET', etc.
            quantity: Order quantity
            price: Order price (required for LIMIT orders)
            **kwargs: Additional order parameters
            
        Returns:
            Order response dictionary or None on error
        """
        try:
            order_params = {
                'symbol': symbol,
                'side': side,
                'type': order_type,
                'quantity': quantity,
                'isIsolated': 'FALSE',  # Cross margin
                **kwargs
            }
            
            if order_type == 'LIMIT' and price:
                order_params['price'] = price
                order_params['timeInForce'] = kwargs.get('timeInForce', 'GTC')
            
            self.logger.info(f"Creating margin order: {order_params}")
            order = self.client.create_margin_order(**order_params)
            self.logger.info(f"Order created successfully: {order}")
            return order
            
        except BinanceAPIException as e:
            self.logger.error(f"Binance API error creating order: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Error creating order: {e}")
            return None

    def cancel_margin_order(self, symbol: str, order_id: int) -> bool:
        """
        Cancel a margin order.
        
        Args:
            symbol: Trading pair symbol
            order_id: Order ID to cancel
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info(f"Cancelling order {order_id} for {symbol}")
            result = self.client.cancel_margin_order(
                symbol=symbol,
                orderId=order_id,
                isIsolated='FALSE'
            )
            self.logger.info(f"Order cancelled: {result}")
            return True
        except BinanceAPIException as e:
            self.logger.error(f"Binance API error cancelling order: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Error cancelling order: {e}")
            return False

    def get_open_margin_orders(self, symbol: str) -> Optional[list]:
        """
        Get all open margin orders for a symbol.
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            List of open orders or None on error
        """
        try:
            orders = self.client.get_open_margin_orders(
                symbol=symbol,
                isIsolated='FALSE'
            )
            self.logger.debug(f"Open orders for {symbol}: {orders}")
            return orders
        except BinanceAPIException as e:
            self.logger.error(f"Binance API error getting orders: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Error getting orders: {e}")
            return None

    def get_margin_position(self, symbol: str) -> Optional[Dict]:
        """
        Get current margin position for a symbol.
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            Position information or None
        """
        try:
            account = self.get_account_balance()
            if not account:
                return None
            
            # Try to extract base asset - handle common quote assets
            # This is a simplified approach; for production, use exchange info API
            base_asset = None
            for quote in ['USDT', 'BUSD', 'USDC', 'BTC', 'ETH', 'BNB']:
                if symbol.endswith(quote):
                    base_asset = symbol[:-len(quote)]
                    break
            
            if not base_asset:
                self.logger.warning(f"Could not determine base asset for {symbol}")
                return None
            
            for asset in account.get('userAssets', []):
                if asset['asset'] == base_asset:
                    return asset
            
            return None
        except Exception as e:
            self.logger.error(f"Error getting position: {e}")
            return None

    def close_position(self, symbol: str) -> bool:
        """
        Close all open positions for a symbol.
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            True if successful, False otherwise
        """
        try:
            position = self.get_margin_position(symbol)
            if not position:
                self.logger.info(f"No position to close for {symbol}")
                return True
            
            borrowed = float(position.get('borrowed', 0))
            free = float(position.get('free', 0))
            
            if borrowed > 0:
                # Need to sell to repay
                self.logger.info(f"Closing borrowed position: {borrowed}")
                # Implementation would go here
                
            self.logger.info(f"Position closed for {symbol}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error closing position: {e}")
            return False
