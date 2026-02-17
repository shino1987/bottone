"""
Step 1: Market Structure Validation Filter
Validates market conditions before entering the 7-step strategy.
"""

from typing import Dict, Any, Optional, List
import logging
from filters.base_filter import BaseFilter


class MarketStructureFilter(BaseFilter):
    """
    Step 1 - Market Structure Validation
    - Validate minimum volume (1M USDT)
    - Identify market structure (ranging/trending_up/trending_down)
    - Check for abnormal gaps
    - Verify sufficient price movement
    """

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """Initialize market structure filter with parameters."""
        default_params = {
            'min_volume_usdt': 1_000_000,  # 1M USDT minimum volume
            'min_price_movement': 0.5,  # 0.5% minimum price movement
            'max_gap_threshold': 2.0,  # 2% maximum gap threshold
        }
        if params:
            default_params.update(params)
        super().__init__("MarketStructure", default_params)

    def analyze(self, market_data: Dict[str, Any]) -> bool:
        """
        Analyze market structure and return if conditions are met.
        
        Args:
            market_data: Dictionary containing:
                - candles: List of OHLCV candles
                - symbol: Trading pair symbol
                
        Returns:
            True if market structure is valid, False otherwise
        """
        if not self.validate_market_data(market_data, ['candles']):
            return False

        candles = market_data['candles']
        if len(candles) < 20:
            self.logger.warning("Insufficient candles for market structure analysis")
            return False

        # Validate minimum volume
        if not self._check_volume(candles):
            self.logger.info("Volume threshold not met")
            return False

        # Check for abnormal gaps
        if self._has_abnormal_gaps(candles):
            self.logger.warning("Abnormal gaps detected in price action")
            return False

        # Verify sufficient price movement
        if not self._check_price_movement(candles):
            self.logger.info("Insufficient price movement")
            return False

        # Identify market structure
        structure = self._identify_structure(candles)
        self.logger.info(f"Market structure identified: {structure}")

        return True

    def get_signal(self, market_data: Dict[str, Any]) -> str:
        """
        Get signal from market structure filter.
        
        Args:
            market_data: Dictionary containing market data
            
        Returns:
            'HOLD' - This is a validation filter, not a signal generator
        """
        if self.analyze(market_data):
            return 'HOLD'  # Pass validation, continue to next step
        return 'HOLD'

    def _check_volume(self, candles: List[Dict[str, Any]]) -> bool:
        """Check if volume meets minimum threshold."""
        min_volume = self.params['min_volume_usdt']
        
        # Calculate average volume over last 20 candles
        recent_candles = candles[-20:]
        total_volume = sum(float(c.get('volume', 0)) * float(c.get('close', 0)) 
                          for c in recent_candles)
        avg_volume = total_volume / len(recent_candles)
        
        self.logger.debug(f"Average volume: {avg_volume:.2f} USDT (min: {min_volume})")
        return avg_volume >= min_volume

    def _has_abnormal_gaps(self, candles: List[Dict[str, Any]]) -> bool:
        """Check for abnormal gaps in price action."""
        max_gap = self.params['max_gap_threshold']
        
        for i in range(1, len(candles)):
            prev_close = float(candles[i-1]['close'])
            curr_open = float(candles[i]['open'])
            
            # Calculate gap percentage
            gap_pct = abs(curr_open - prev_close) / prev_close * 100
            
            if gap_pct > max_gap:
                self.logger.warning(f"Abnormal gap detected: {gap_pct:.2f}%")
                return True
        
        return False

    def _check_price_movement(self, candles: List[Dict[str, Any]]) -> bool:
        """Verify sufficient price movement."""
        min_movement = self.params['min_price_movement']
        
        # Calculate price movement over last 20 candles
        recent_candles = candles[-20:]
        high = max(float(c['high']) for c in recent_candles)
        low = min(float(c['low']) for c in recent_candles)
        
        price_range = (high - low) / low * 100
        
        self.logger.debug(f"Price movement: {price_range:.2f}% (min: {min_movement}%)")
        return price_range >= min_movement

    def _identify_structure(self, candles: List[Dict[str, Any]]) -> str:
        """
        Identify market structure (ranging/trending_up/trending_down).
        
        Returns:
            Market structure type as string
        """
        # Use last 20 candles for structure identification
        recent_candles = candles[-20:]
        
        # Calculate simple moving average slope
        closes = [float(c['close']) for c in recent_candles]
        
        # Calculate slope using first and last values
        first_close = closes[0]
        last_close = closes[-1]
        slope = (last_close - first_close) / first_close * 100
        
        # Determine structure based on slope
        if slope > 1.0:
            return "trending_up"
        elif slope < -1.0:
            return "trending_down"
        else:
            return "ranging"

    def get_market_structure(self, market_data: Dict[str, Any]) -> Optional[str]:
        """
        Get current market structure type.
        
        Args:
            market_data: Dictionary containing candles
            
        Returns:
            Market structure type or None
        """
        if not self.validate_market_data(market_data, ['candles']):
            return None
        
        candles = market_data['candles']
        if len(candles) < 20:
            return None
        
        return self._identify_structure(candles)
