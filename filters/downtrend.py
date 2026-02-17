"""
Step 2: Downtrend Detection Filter
Detects downtrend with consecutive lower lows and lower highs.
"""

from typing import Dict, Any, Optional, List
import logging
from filters.base_filter import BaseFilter


class DowntrendFilter(BaseFilter):
    """
    Step 2 - Downtrend Detection
    - Detect 2-3 consecutive lower lows
    - Detect 2-3 consecutive lower highs
    - Confirm with negative MA slope (20-period)
    - Return TRUE when downtrend confirmed
    """

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """Initialize downtrend filter with parameters."""
        default_params = {
            'min_consecutive_lows': 2,  # Minimum consecutive lower lows
            'max_consecutive_lows': 3,  # Maximum to check
            'ma_period': 20,  # Moving average period
            'ma_slope_threshold': -0.5,  # Negative slope threshold (%)
        }
        if params:
            default_params.update(params)
        super().__init__("Downtrend", default_params)

    def analyze(self, market_data: Dict[str, Any]) -> bool:
        """
        Analyze market data for downtrend pattern.
        
        Args:
            market_data: Dictionary containing:
                - candles: List of OHLCV candles
                
        Returns:
            True if downtrend is confirmed, False otherwise
        """
        if not self.validate_market_data(market_data, ['candles']):
            return False

        candles = market_data['candles']
        if len(candles) < 30:
            self.logger.warning("Insufficient candles for downtrend analysis")
            return False

        # Check for consecutive lower lows
        has_lower_lows = self._check_lower_lows(candles)
        
        # Check for consecutive lower highs
        has_lower_highs = self._check_lower_highs(candles)
        
        # Check MA slope
        has_negative_ma = self._check_ma_slope(candles)
        
        # All conditions must be met
        is_downtrend = has_lower_lows and has_lower_highs and has_negative_ma
        
        if is_downtrend:
            self.logger.info("Downtrend confirmed: lower lows, lower highs, and negative MA")
        else:
            self.logger.debug(f"Downtrend not confirmed: LL={has_lower_lows}, LH={has_lower_highs}, MA={has_negative_ma}")
        
        return is_downtrend

    def get_signal(self, market_data: Dict[str, Any]) -> str:
        """
        Get signal from downtrend filter.
        
        Args:
            market_data: Dictionary containing market data
            
        Returns:
            'HOLD' - This is a validation filter, continues to next step if True
        """
        if self.analyze(market_data):
            return 'HOLD'  # Downtrend confirmed, continue to next step
        return 'HOLD'

    def _check_lower_lows(self, candles: List[Dict[str, Any]]) -> bool:
        """
        Check for consecutive lower lows.
        
        Returns:
            True if pattern found, False otherwise
        """
        min_consecutive = self.params['min_consecutive_lows']
        max_consecutive = self.params['max_consecutive_lows']
        
        # Find swing lows (local minima)
        swing_lows = self._find_swing_lows(candles[-30:])
        
        if len(swing_lows) < min_consecutive:
            return False
        
        # Check if we have consecutive lower lows
        consecutive_count = 0
        for i in range(1, min(len(swing_lows), max_consecutive + 1)):
            if swing_lows[-i] < swing_lows[-i-1] if i < len(swing_lows) else False:
                consecutive_count += 1
            else:
                break
        
        result = consecutive_count >= min_consecutive
        self.logger.debug(f"Lower lows check: {consecutive_count} consecutive (need {min_consecutive})")
        return result

    def _check_lower_highs(self, candles: List[Dict[str, Any]]) -> bool:
        """
        Check for consecutive lower highs.
        
        Returns:
            True if pattern found, False otherwise
        """
        min_consecutive = self.params['min_consecutive_lows']
        max_consecutive = self.params['max_consecutive_lows']
        
        # Find swing highs (local maxima)
        swing_highs = self._find_swing_highs(candles[-30:])
        
        if len(swing_highs) < min_consecutive:
            return False
        
        # Check if we have consecutive lower highs
        consecutive_count = 0
        for i in range(1, min(len(swing_highs), max_consecutive + 1)):
            if swing_highs[-i] < swing_highs[-i-1] if i < len(swing_highs) else False:
                consecutive_count += 1
            else:
                break
        
        result = consecutive_count >= min_consecutive
        self.logger.debug(f"Lower highs check: {consecutive_count} consecutive (need {min_consecutive})")
        return result

    def _find_swing_lows(self, candles: List[Dict[str, Any]], window: int = 2) -> List[float]:
        """
        Find swing lows (local minima) in price data.
        
        Args:
            candles: List of candles
            window: Window size for local minima detection
            
        Returns:
            List of swing low prices
        """
        swing_lows = []
        
        for i in range(window, len(candles) - window):
            current_low = float(candles[i]['low'])
            
            # Check if current low is lower than surrounding candles
            is_swing_low = True
            for j in range(i - window, i + window + 1):
                if j != i and float(candles[j]['low']) < current_low:
                    is_swing_low = False
                    break
            
            if is_swing_low:
                swing_lows.append(current_low)
        
        return swing_lows

    def _find_swing_highs(self, candles: List[Dict[str, Any]], window: int = 2) -> List[float]:
        """
        Find swing highs (local maxima) in price data.
        
        Args:
            candles: List of candles
            window: Window size for local maxima detection
            
        Returns:
            List of swing high prices
        """
        swing_highs = []
        
        for i in range(window, len(candles) - window):
            current_high = float(candles[i]['high'])
            
            # Check if current high is higher than surrounding candles
            is_swing_high = True
            for j in range(i - window, i + window + 1):
                if j != i and float(candles[j]['high']) > current_high:
                    is_swing_high = False
                    break
            
            if is_swing_high:
                swing_highs.append(current_high)
        
        return swing_highs

    def _check_ma_slope(self, candles: List[Dict[str, Any]]) -> bool:
        """
        Check moving average slope for negative trend.
        
        Returns:
            True if MA slope is negative, False otherwise
        """
        ma_period = self.params['ma_period']
        threshold = self.params['ma_slope_threshold']
        
        if len(candles) < ma_period + 5:
            return False
        
        # Calculate MA values
        closes = [float(c['close']) for c in candles]
        ma_values = []
        
        for i in range(ma_period, len(closes)):
            ma = sum(closes[i-ma_period:i]) / ma_period
            ma_values.append(ma)
        
        if len(ma_values) < 2:
            return False
        
        # Calculate slope (percentage change)
        first_ma = ma_values[-5] if len(ma_values) >= 5 else ma_values[0]
        last_ma = ma_values[-1]
        slope = (last_ma - first_ma) / first_ma * 100
        
        result = slope < threshold
        self.logger.debug(f"MA slope: {slope:.2f}% (threshold: {threshold}%)")
        return result

    def get_last_swing_low(self, market_data: Dict[str, Any]) -> Optional[float]:
        """
        Get the most recent swing low price.
        
        Args:
            market_data: Dictionary containing candles
            
        Returns:
            Last swing low price or None
        """
        if not self.validate_market_data(market_data, ['candles']):
            return None
        
        candles = market_data['candles']
        if len(candles) < 10:
            return None
        
        swing_lows = self._find_swing_lows(candles[-30:])
        return swing_lows[-1] if swing_lows else None
