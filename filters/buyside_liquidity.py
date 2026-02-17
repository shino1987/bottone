"""
Buyside Liquidity Filter - Identifies liquidity zones at recent swing lows.

This filter analyzes 15-minute candlestick data to identify swing lows and
calculate liquidity zones based on volume and support levels.
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
from filters.base_filter import BaseFilter


class BuysideLiquidityFilter(BaseFilter):
    """
    Filter to identify buyside liquidity zones at swing lows.
    
    Analyzes OHLCV data to find:
    - Swing lows (local minima in price)
    - Liquidity zones based on volume clustering
    - Support levels
    """
    
    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """
        Initialize the buyside liquidity filter.
        
        Args:
            params: Optional parameters including:
                - swing_period: Number of candles to consider for swing detection (default: 5)
                - min_swing_count: Minimum number of swing lows to find (default: 5)
                - volume_threshold: Volume multiplier for liquidity zones (default: 1.2)
        """
        default_params = {
            'swing_period': 5,
            'min_swing_count': 5,
            'volume_threshold': 1.2
        }
        if params:
            default_params.update(params)
        
        super().__init__("BuysideLiquidityFilter", default_params)
        
        self.swing_period = self.params['swing_period']
        self.min_swing_count = self.params['min_swing_count']
        self.volume_threshold = self.params['volume_threshold']
    
    def analyze(self, market_data: Dict[str, Any]) -> bool:
        """
        Analyze market data to determine if buyside liquidity conditions are met.
        
        Args:
            market_data: Dictionary containing OHLCV data
            
        Returns:
            True if buyside liquidity is found, False otherwise
        """
        if not self.validate_market_data(market_data, ['ohlcv']):
            self.logger.warning("OHLCV data not available in market_data")
            return False
        
        ohlcv = market_data['ohlcv']
        
        if len(ohlcv) < self.swing_period * 2:
            self.logger.warning(f"Insufficient data: {len(ohlcv)} candles, need at least {self.swing_period * 2}")
            return False
        
        # Find swing lows
        swing_lows = self.find_swing_lows(ohlcv)
        
        if len(swing_lows) < self.min_swing_count:
            self.logger.debug(f"Found only {len(swing_lows)} swing lows, need at least {self.min_swing_count}")
            return False
        
        # Calculate liquidity zones
        liquidity_zone = self.calculate_liquidity_zone(ohlcv, swing_lows)
        
        return liquidity_zone is not None
    
    def get_signal(self, market_data: Dict[str, Any]) -> str:
        """
        Get trading signal based on buyside liquidity analysis.
        
        Args:
            market_data: Dictionary containing OHLCV data
            
        Returns:
            'BUY' if liquidity found, 'HOLD' otherwise
        """
        if self.analyze(market_data):
            self.logger.info("Buyside liquidity detected")
            return 'BUY'
        return 'HOLD'
    
    def find_swing_lows(self, ohlcv: List[Dict[str, Any]]) -> List[Tuple[int, float]]:
        """
        Identify swing lows in the OHLCV data.
        
        A swing low is a local minimum where the low is lower than
        the lows of surrounding candles within the swing_period.
        
        Args:
            ohlcv: List of OHLCV dictionaries
            
        Returns:
            List of tuples (index, low_price) for each swing low
        """
        swing_lows = []
        
        # Start from swing_period to have enough data on both sides
        for i in range(self.swing_period, len(ohlcv) - self.swing_period):
            current_low = ohlcv[i]['low']
            
            # Check if this is a local minimum
            is_swing_low = True
            
            # Check previous candles
            for j in range(i - self.swing_period, i):
                if ohlcv[j]['low'] < current_low:
                    is_swing_low = False
                    break
            
            # Check following candles
            if is_swing_low:
                for j in range(i + 1, min(i + self.swing_period + 1, len(ohlcv))):
                    if ohlcv[j]['low'] < current_low:
                        is_swing_low = False
                        break
            
            if is_swing_low:
                swing_lows.append((i, current_low))
        
        self.logger.debug(f"Found {len(swing_lows)} swing lows")
        return swing_lows
    
    def calculate_liquidity_zone(
        self,
        ohlcv: List[Dict[str, Any]],
        swing_lows: List[Tuple[int, float]]
    ) -> Optional[Dict[str, Any]]:
        """
        Calculate liquidity zone based on swing lows and volume.
        
        Args:
            ohlcv: List of OHLCV dictionaries
            swing_lows: List of swing low tuples (index, price)
            
        Returns:
            Dictionary with liquidity zone information or None
        """
        if not swing_lows:
            return None
        
        # Calculate average volume
        total_volume = sum(candle['volume'] for candle in ohlcv)
        avg_volume = total_volume / len(ohlcv)
        
        # Find the most recent swing lows with high volume
        liquidity_candidates = []
        
        for idx, low_price in swing_lows[-self.min_swing_count:]:
            candle = ohlcv[idx]
            
            # Check if volume is above threshold
            if candle['volume'] >= avg_volume * self.volume_threshold:
                liquidity_candidates.append({
                    'index': idx,
                    'price': low_price,
                    'volume': candle['volume'],
                    'timestamp': candle['timestamp']
                })
        
        if not liquidity_candidates:
            self.logger.debug("No liquidity candidates found with sufficient volume")
            return None
        
        # Return the most recent liquidity zone
        liquidity_zone = liquidity_candidates[-1]
        
        self.logger.info(
            f"Liquidity zone identified at price {liquidity_zone['price']:.2f} "
            f"with volume {liquidity_zone['volume']:.2f}"
        )
        
        return liquidity_zone
    
    def get_liquidity_price(self, market_data: Dict[str, Any]) -> Optional[float]:
        """
        Get the price level of the identified liquidity zone.
        
        Args:
            market_data: Dictionary containing OHLCV data
            
        Returns:
            Price of liquidity zone or None if not found
        """
        if not self.validate_market_data(market_data, ['ohlcv']):
            return None
        
        ohlcv = market_data['ohlcv']
        
        if len(ohlcv) < self.swing_period * 2:
            return None
        
        swing_lows = self.find_swing_lows(ohlcv)
        liquidity_zone = self.calculate_liquidity_zone(ohlcv, swing_lows)
        
        if liquidity_zone:
            return liquidity_zone['price']
        
        return None
    
    def calculate_support_resistance(
        self,
        ohlcv: List[Dict[str, Any]]
    ) -> Tuple[List[float], List[float]]:
        """
        Calculate support and resistance levels from OHLCV data.
        
        Args:
            ohlcv: List of OHLCV dictionaries
            
        Returns:
            Tuple of (support_levels, resistance_levels)
        """
        # Find all swing lows (support) and swing highs (resistance)
        swing_lows = self.find_swing_lows(ohlcv)
        swing_highs = self.find_swing_highs(ohlcv)
        
        support_levels = [price for _, price in swing_lows]
        resistance_levels = [price for _, price in swing_highs]
        
        return support_levels, resistance_levels
    
    def find_swing_highs(self, ohlcv: List[Dict[str, Any]]) -> List[Tuple[int, float]]:
        """
        Identify swing highs in the OHLCV data.
        
        A swing high is a local maximum where the high is higher than
        the highs of surrounding candles within the swing_period.
        
        Args:
            ohlcv: List of OHLCV dictionaries
            
        Returns:
            List of tuples (index, high_price) for each swing high
        """
        swing_highs = []
        
        for i in range(self.swing_period, len(ohlcv) - self.swing_period):
            current_high = ohlcv[i]['high']
            
            # Check if this is a local maximum
            is_swing_high = True
            
            # Check previous candles
            for j in range(i - self.swing_period, i):
                if ohlcv[j]['high'] > current_high:
                    is_swing_high = False
                    break
            
            # Check following candles
            if is_swing_high:
                for j in range(i + 1, min(i + self.swing_period + 1, len(ohlcv))):
                    if ohlcv[j]['high'] > current_high:
                        is_swing_high = False
                        break
            
            if is_swing_high:
                swing_highs.append((i, current_high))
        
        return swing_highs
