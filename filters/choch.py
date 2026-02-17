"""
Step 4: Change of Character (CHOCH) Detection Filter
Detects market structure break and trend rotation.
"""

from typing import Dict, Any, Optional, List
import logging
from filters.base_filter import BaseFilter


class CHOCHFilter(BaseFilter):
    """
    Step 4 - Change of Character (CHOCH) Detection
    - Monitor market structure (structure break)
    - Identify trend rotation
    - Candle close above last swing low
    - Return TRUE when CHOCH verified
    """

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """Initialize CHOCH filter with parameters."""
        default_params = {
            'confirmation_candles': 1,  # Candles needed to confirm CHOCH
            'structure_lookback': 15,  # Candles to analyze for structure
            'min_break_percentage': 0.2,  # Minimum % break above swing low
        }
        if params:
            default_params.update(params)
        super().__init__("CHOCH", default_params)
        
        self.choch_detected = False
        self.choch_price = None

    def analyze(self, market_data: Dict[str, Any]) -> bool:
        """
        Analyze market data for CHOCH pattern.
        
        Args:
            market_data: Dictionary containing:
                - candles: List of OHLCV candles
                - last_swing_low: Optional last swing low price
                
        Returns:
            True if CHOCH is detected, False otherwise
        """
        if not self.validate_market_data(market_data, ['candles']):
            return False

        candles = market_data['candles']
        if len(candles) < 20:
            self.logger.warning("Insufficient candles for CHOCH analysis")
            return False

        # Get last swing low from market data or detect it
        last_swing_low = market_data.get('last_swing_low')
        if not last_swing_low:
            last_swing_low = self._find_last_swing_low(candles)
        
        if not last_swing_low:
            self.logger.debug("No swing low found for CHOCH detection")
            return False

        # Check for structure break (close above swing low)
        structure_break = self._check_structure_break(candles, last_swing_low)
        if not structure_break:
            self.logger.debug("No structure break detected")
            return False

        # Verify trend rotation
        trend_rotation = self._verify_trend_rotation(candles)
        if not trend_rotation:
            self.logger.debug("Trend rotation not confirmed")
            return False

        self.choch_detected = True
        self.choch_price = last_swing_low
        
        self.logger.info(f"CHOCH detected at {last_swing_low:.4f} - structure break confirmed")
        return True

    def get_signal(self, market_data: Dict[str, Any]) -> str:
        """
        Get signal from CHOCH filter.
        
        Args:
            market_data: Dictionary containing market data
            
        Returns:
            'HOLD' - This is a validation filter
        """
        if self.analyze(market_data):
            return 'HOLD'  # CHOCH detected, continue to next step
        return 'HOLD'

    def _find_last_swing_low(self, candles: List[Dict[str, Any]]) -> Optional[float]:
        """
        Find the last swing low in recent price action.
        
        Returns:
            Swing low price or None
        """
        lookback = self.params['structure_lookback']
        window = 2
        
        recent_candles = candles[-(lookback + window * 2):]
        
        # Find most recent swing low
        for i in range(len(recent_candles) - window - 1, window, -1):
            current_low = float(recent_candles[i]['low'])
            
            # Check if this is a local minimum
            is_swing_low = True
            for j in range(i - window, i + window + 1):
                if j != i and j >= 0 and j < len(recent_candles):
                    if float(recent_candles[j]['low']) < current_low:
                        is_swing_low = False
                        break
            
            if is_swing_low:
                return current_low
        
        return None

    def _check_structure_break(self, candles: List[Dict[str, Any]], 
                               swing_low: float) -> bool:
        """
        Check if price has broken above the swing low structure.
        
        Args:
            candles: List of candles
            swing_low: Swing low price level
            
        Returns:
            True if structure break confirmed, False otherwise
        """
        confirmation_candles = self.params['confirmation_candles']
        min_break_pct = self.params['min_break_percentage']
        
        break_level = swing_low * (1 + min_break_pct / 100)
        
        # Check recent candles for close above swing low
        recent_candles = candles[-confirmation_candles:]
        
        for candle in recent_candles:
            close = float(candle['close'])
            
            # Structure break confirmed by close above swing low
            if close > break_level:
                self.logger.debug(f"Structure break: close={close:.4f} > break_level={break_level:.4f}")
                return True
        
        return False

    def _verify_trend_rotation(self, candles: List[Dict[str, Any]]) -> bool:
        """
        Verify trend rotation from downtrend to potential uptrend.
        
        Args:
            candles: List of candles
            
        Returns:
            True if rotation detected, False otherwise
        """
        lookback = self.params['structure_lookback']
        
        if len(candles) < lookback:
            return False
        
        recent_candles = candles[-lookback:]
        
        # Calculate price momentum
        first_close = float(recent_candles[0]['close'])
        last_close = float(recent_candles[-1]['close'])
        
        # Simple check: recent price higher than earlier price
        momentum = (last_close - first_close) / first_close * 100
        
        # Also check recent candles show buying pressure
        bullish_candles = 0
        for candle in recent_candles[-5:]:
            if float(candle['close']) > float(candle['open']):
                bullish_candles += 1
        
        # Rotation confirmed if positive momentum and majority bullish candles
        rotation_confirmed = momentum > 0 and bullish_candles >= 3
        
        self.logger.debug(f"Trend rotation check: momentum={momentum:.2f}%, bullish_candles={bullish_candles}/5")
        return rotation_confirmed

    def get_choch_price(self) -> Optional[float]:
        """
        Get the price level where CHOCH was detected.
        
        Returns:
            CHOCH price or None
        """
        return self.choch_price if self.choch_detected else None

    def is_choch_detected(self) -> bool:
        """
        Check if CHOCH has been detected.
        
        Returns:
            True if CHOCH detected, False otherwise
        """
        return self.choch_detected

    def reset(self):
        """Reset filter state."""
        self.choch_detected = False
        self.choch_price = None
