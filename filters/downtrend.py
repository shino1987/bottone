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
        self.state_data = {}  # State tracking data

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
        if len(candles) < 10:
            return False

        # 1️⃣ CHECK FOR LOWER LOWS
        has_lower_lows = self._check_lower_lows(candles)
        
        # 2️⃣ CHECK FOR LOWER HIGHS
        has_lower_highs = self._check_lower_highs(candles)
        
        # 3️⃣ CHECK MA SLOPE
        has_negative_ma = self._check_ma_slope(candles)
        
        # Downtrend confirmed if ANY condition is met
        is_downtrend = has_lower_lows or has_lower_highs or has_negative_ma
        
        if is_downtrend:
            self.logger.info(f"Step 2 confirmed: Downtrend detected (LL={has_lower_lows}, LH={has_lower_highs}, MA={has_negative_ma})")
            self.state_data['downtrend_confirmed'] = True
        
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
        """Check for consecutive lower lows in recent candles."""
        if len(candles) < 4:
            return False
        
        # Get last 4 candles' lows
        lows = [float(c['low']) for c in candles[-4:]]
        
        # Check if lows are progressively decreasing
        lower_count = 0
        for i in range(1, len(lows)):
            if lows[i] < lows[i-1]:
                lower_count += 1
        
        result = lower_count >= 2  # At least 2 lower lows
        self.logger.debug(f"Lower lows check: {lower_count} consecutive lower lows")
        return result

    def _check_lower_highs(self, candles: List[Dict[str, Any]]) -> bool:
        """Check for consecutive lower highs in recent candles."""
        if len(candles) < 4:
            return False
        
        # Get last 4 candles' highs
        highs = [float(c['high']) for c in candles[-4:]]
        
        # Check if highs are progressively decreasing
        lower_count = 0
        for i in range(1, len(highs)):
            if highs[i] < highs[i-1]:
                lower_count += 1
        
        result = lower_count >= 2  # At least 2 lower highs
        self.logger.debug(f"Lower highs check: {lower_count} consecutive lower highs")
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
        """Check moving average slope for negative trend."""
        ma_period = self.params['ma_period']
        
        if len(candles) < ma_period:
            return False
        
        # Calculate simple moving average
        closes = [float(c['close']) for c in candles[-ma_period:]]
        ma_current = sum(closes) / len(closes)
        
        # Compare with MA 10 candles ago
        if len(candles) < ma_period + 10:
            return False
        
        closes_prev = [float(c['close']) for c in candles[-(ma_period+10):-10]]
        ma_previous = sum(closes_prev) / len(closes_prev)
        
        # Negative slope if current MA < previous MA
        slope = ma_current - ma_previous
        result = slope < 0
        
        self.logger.debug(f"MA slope: {slope:.2f} (negative={result})")
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
