"""
Step 5: Market Structure Shift (MMS) Detection Filter
Identifies the first higher low after CHOCH to confirm structure rotation.
"""

from typing import Dict, Any, Optional, List
import logging
from filters.base_filter import BaseFilter


class MMSFilter(BaseFilter):
    """
    Step 5 - Market Structure Shift (MMS) Detection
    - Identify first higher low after CHOCH
    - Confirm structure rotation
    - Return TRUE when MMS formed
    """

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """Initialize MMS filter with parameters."""
        default_params = {
            'min_candles_after_choch': 3,  # Minimum candles after CHOCH
            'max_candles_lookback': 10,  # Maximum candles to look back for higher low
            'higher_low_threshold': 0.1,  # Minimum % higher than previous low
        }
        if params:
            default_params.update(params)
        super().__init__("MMS", default_params)
        
        self.mms_detected = False
        self.mms_price = None
        self.higher_low_price = None

    def analyze(self, market_data: Dict[str, Any]) -> bool:
        """
        Analyze market data for MMS pattern.
        
        Args:
            market_data: Dictionary containing:
                - candles: List of OHLCV candles
                - choch_price: CHOCH price level (from previous step)
                
        Returns:
            True if MMS is detected, False otherwise
        """
        if not self.validate_market_data(market_data, ['candles']):
            return False

        candles = market_data['candles']
        if len(candles) < 15:
            self.logger.warning("Insufficient candles for MMS analysis")
            return False

        # Get CHOCH price from market data
        choch_price = market_data.get('choch_price')
        if not choch_price:
            # Try to estimate from recent swing low
            choch_price = self._estimate_choch_level(candles)
        
        if not choch_price:
            self.logger.debug("No CHOCH price available for MMS detection")
            return False

        # Find previous low before potential higher low
        previous_low = self._find_previous_low(candles)
        if not previous_low:
            self.logger.debug("No previous low found")
            return False

        # Check for higher low formation
        higher_low = self._check_higher_low(candles, previous_low)
        if not higher_low:
            self.logger.debug("No higher low detected")
            return False

        self.higher_low_price = higher_low
        
        # Confirm structure rotation
        structure_confirmed = self._confirm_structure_rotation(candles, choch_price, higher_low)
        if not structure_confirmed:
            self.logger.debug("Structure rotation not confirmed")
            return False

        self.mms_detected = True
        self.mms_price = higher_low
        
        self.logger.info(f"MMS detected: higher low at {higher_low:.4f} (previous: {previous_low:.4f})")
        return True

    def get_signal(self, market_data: Dict[str, Any]) -> str:
        """
        Get signal from MMS filter.
        
        Args:
            market_data: Dictionary containing market data
            
        Returns:
            'HOLD' - This is a validation filter
        """
        if self.analyze(market_data):
            return 'HOLD'  # MMS detected, continue to next step
        return 'HOLD'

    def _estimate_choch_level(self, candles: List[Dict[str, Any]]) -> Optional[float]:
        """
        Estimate CHOCH level from recent swing low.
        
        Returns:
            Estimated CHOCH price or None
        """
        window = 2
        recent_candles = candles[-15:]
        
        for i in range(len(recent_candles) - window - 1, window, -1):
            current_low = float(recent_candles[i]['low'])
            
            is_swing_low = True
            for j in range(i - window, i + window + 1):
                if j != i and j >= 0 and j < len(recent_candles):
                    if float(recent_candles[j]['low']) < current_low:
                        is_swing_low = False
                        break
            
            if is_swing_low:
                return current_low
        
        return None

    def _find_previous_low(self, candles: List[Dict[str, Any]]) -> Optional[float]:
        """
        Find the previous low before the potential higher low.
        
        Returns:
            Previous low price or None
        """
        max_lookback = self.params['max_candles_lookback']
        window = 2
        
        recent_candles = candles[-max_lookback:]
        
        # Find all swing lows
        swing_lows = []
        for i in range(window, len(recent_candles) - window):
            current_low = float(recent_candles[i]['low'])
            
            is_swing_low = True
            for j in range(i - window, i + window + 1):
                if j != i:
                    if float(recent_candles[j]['low']) < current_low:
                        is_swing_low = False
                        break
            
            if is_swing_low:
                swing_lows.append(current_low)
        
        # Return the second-to-last swing low if available
        if len(swing_lows) >= 2:
            return swing_lows[-2]
        elif len(swing_lows) == 1:
            return swing_lows[0]
        
        return None

    def _check_higher_low(self, candles: List[Dict[str, Any]], 
                          previous_low: float) -> Optional[float]:
        """
        Check for higher low formation.
        
        Args:
            candles: List of candles
            previous_low: Previous low price
            
        Returns:
            Higher low price or None
        """
        threshold = self.params['higher_low_threshold']
        min_candles = self.params['min_candles_after_choch']
        window = 2
        
        # Look for higher low in recent candles
        recent_candles = candles[-10:]
        
        for i in range(window, len(recent_candles) - window):
            current_low = float(recent_candles[i]['low'])
            
            # Check if it's a local low
            is_local_low = True
            for j in range(i - window, i + window + 1):
                if j != i and j >= 0 and j < len(recent_candles):
                    if float(recent_candles[j]['low']) < current_low:
                        is_local_low = False
                        break
            
            if is_local_low:
                # Check if it's higher than previous low
                required_level = previous_low * (1 + threshold / 100)
                if current_low >= required_level:
                    self.logger.debug(f"Higher low found: {current_low:.4f} > {required_level:.4f}")
                    return current_low
        
        return None

    def _confirm_structure_rotation(self, candles: List[Dict[str, Any]], 
                                    choch_price: float, 
                                    higher_low: float) -> bool:
        """
        Confirm that structure is rotating to uptrend.
        
        Args:
            candles: List of candles
            choch_price: CHOCH price level
            higher_low: Higher low price
            
        Returns:
            True if confirmed, False otherwise
        """
        # Check that higher low is above CHOCH price
        if higher_low <= choch_price:
            return False
        
        # Check recent price action shows bullish momentum
        recent_candles = candles[-5:]
        bullish_count = sum(1 for c in recent_candles 
                          if float(c['close']) > float(c['open']))
        
        # At least 3 out of 5 recent candles should be bullish
        confirmed = bullish_count >= 3
        
        self.logger.debug(f"Structure rotation: {bullish_count}/5 bullish candles")
        return confirmed

    def get_mms_price(self) -> Optional[float]:
        """
        Get the price level where MMS was detected.
        
        Returns:
            MMS price or None
        """
        return self.mms_price if self.mms_detected else None

    def get_higher_low_price(self) -> Optional[float]:
        """
        Get the higher low price.
        
        Returns:
            Higher low price or None
        """
        return self.higher_low_price

    def is_mms_detected(self) -> bool:
        """
        Check if MMS has been detected.
        
        Returns:
            True if MMS detected, False otherwise
        """
        return self.mms_detected

    def reset(self):
        """Reset filter state."""
        self.mms_detected = False
        self.mms_price = None
        self.higher_low_price = None
