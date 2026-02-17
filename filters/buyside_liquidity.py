"""
Step 1: Buyside Liquidity Detection Filter
Identifies BUYSIDE LIQUIDITY at SWING HIGHS with high volume.
"""

from typing import Dict, Any, Optional, List
import logging
from filters.base_filter import BaseFilter


class BuysideLiquidityFilter(BaseFilter):
    """
    Step 1 - Buyside Liquidity Detection
    - Identify swing highs (local maximums)
    - Filter by high volume (1.2x average)
    - Track buyside liquidity price for next steps
    """

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """Initialize buyside liquidity filter with parameters."""
        default_params = {
            'volume_multiplier': 1.2,  # 1.2x average volume threshold
            'swing_window': 1,  # Window size for swing high detection
        }
        if params:
            default_params.update(params)
        super().__init__("BuysideLiquidity", default_params)
        
        # Store state data
        self.buyside_liquidity_price = None
        self.buyside_liquidity_volume = None
        self.buyside_liquidity_index = None

    def analyze(self, market_data: Dict[str, Any]) -> bool:
        """
        Step 1: Find BUYSIDE LIQUIDITY at SWING HIGHS
        
        Args:
            market_data: Dictionary containing:
                - candles: List of OHLCV candles (50 candlestick 15min)
                
        Returns:
            True if buyside liquidity is detected, False otherwise
        """
        if not self.validate_market_data(market_data, ['candles']):
            return False

        candles = market_data['candles']
        if len(candles) < 5:
            self.logger.warning("Insufficient candles for buyside liquidity analysis")
            return False

        # 1️⃣ IDENTIFY SWING HIGH (local maximums)
        swing_highs = []
        window = self.params['swing_window']
        
        for i in range(window, len(candles) - window):
            current_high = float(candles[i]['high'])
            
            # Candle is swing high if it's the local maximum
            is_swing_high = True
            
            # Check if higher than previous candles
            for j in range(i - window, i):
                if float(candles[j]['high']) >= current_high:
                    is_swing_high = False
                    break
            
            # Check if higher than next candles
            if is_swing_high:
                for j in range(i + 1, i + window + 1):
                    if float(candles[j]['high']) >= current_high:
                        is_swing_high = False
                        break
            
            if is_swing_high:
                swing_highs.append({
                    'price': current_high,
                    'volume': float(candles[i]['volume']),
                    'index': i
                })
        
        if not swing_highs:
            self.logger.debug("No swing highs found")
            return False
        
        # 2️⃣ FILTER BY VOLUME (buyside = high volume)
        avg_volume = sum(float(c['volume']) for c in candles) / len(candles)
        volume_threshold = avg_volume * self.params['volume_multiplier']
        
        buyside_liquidity = [sh for sh in swing_highs 
                            if sh['volume'] > volume_threshold]
        
        if not buyside_liquidity:
            self.logger.debug(f"No swing highs with volume > {volume_threshold:.2f} (avg: {avg_volume:.2f})")
            return False
        
        # 3️⃣ GET LAST SWING HIGH WITH HIGH VOLUME
        last_buyside = buyside_liquidity[-1]
        self.buyside_liquidity_price = last_buyside['price']
        self.buyside_liquidity_volume = last_buyside['volume']
        self.buyside_liquidity_index = last_buyside['index']
        
        self.logger.info(f"Step 1 confirmed: Buyside liquidity found at price {self.buyside_liquidity_price:.4f} with volume {self.buyside_liquidity_volume:.2f}")
        
        return True

    def get_signal(self, market_data: Dict[str, Any]) -> str:
        """
        Get signal from buyside liquidity filter.
        
        Args:
            market_data: Dictionary containing market data
            
        Returns:
            'HOLD' - This is a validation filter, not a signal generator
        """
        if self.analyze(market_data):
            return 'HOLD'  # Pass validation, continue to next step
        return 'HOLD'

    def get_buyside_liquidity_price(self) -> Optional[float]:
        """
        Get the detected buyside liquidity price.
        
        Returns:
            Buyside liquidity price or None
        """
        return self.buyside_liquidity_price

    def get_buyside_liquidity_data(self) -> Optional[Dict[str, Any]]:
        """
        Get all buyside liquidity data.
        
        Returns:
            Dictionary with buyside liquidity data or None
        """
        if self.buyside_liquidity_price is not None:
            return {
                'price': self.buyside_liquidity_price,
                'volume': self.buyside_liquidity_volume,
                'index': self.buyside_liquidity_index
            }
        return None

    def reset(self):
        """Reset filter state."""
        self.buyside_liquidity_price = None
        self.buyside_liquidity_volume = None
        self.buyside_liquidity_index = None
