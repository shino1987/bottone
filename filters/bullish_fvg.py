"""
Step 6: Bullish Fair Value Gap (FVG) Detection Filter
Identifies bullish fair value gaps and tracks price retracement.
"""

from typing import Dict, Any, Optional, List, Tuple
import logging
from filters.base_filter import BaseFilter


class BullishFVGFilter(BaseFilter):
    """
    Step 6 - Bullish Fair Value Gap (FVG) Detection
    
    Bullish FVG Definition:
    - Formed by 3 closed candles (C1, C2, C3)
    - C1 high < C3 low (gap upward, wicks don't touch)
    - C1 high = bottom of gap
    - C3 low = top of gap
    - Track price retracement in FVG
    - Return 'HOLD' regardless of FVG detection (validation filter)
    """

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """Initialize Bullish FVG filter with parameters."""
        default_params = {
            'min_gap_percentage': 0.1,  # Minimum gap size (%)
            'max_candles_lookback': 10,  # Max candles to look back for FVG
        }
        if params:
            default_params.update(params)
        super().__init__("BullishFVG", default_params)
        
        self.fvg_detected = False
        self.fvg_zone = None

    def analyze(self, market_data: Dict[str, Any]) -> bool:
        """
        Analyze market data for bullish FVG pattern.
        
        Args:
            market_data: Dictionary containing:
                - candles: List of OHLCV candles
                
        Returns:
            True if bullish FVG is detected, False otherwise
        """
        if not self.validate_market_data(market_data, ['candles']):
            return False

        candles = market_data['candles']
        if len(candles) < 10:
            self.logger.warning("Insufficient candles for FVG analysis")
            return False

        # Look for bullish FVG in recent candles
        fvg = self._find_bullish_fvg(candles)
        if not fvg:
            self.logger.debug("No bullish FVG detected")
            return False

        self.fvg_detected = True
        self.fvg_zone = fvg
        
        self.logger.info(f"Bullish FVG detected: {fvg['low']:.4f} - {fvg['high']:.4f}")
        return True

    def get_signal(self, market_data: Dict[str, Any]) -> str:
        """
        Get signal from bullish FVG filter.
        
        Args:
            market_data: Dictionary containing market data
            
        Returns:
            'HOLD' - This is a validation filter that always returns HOLD
            - If FVG NOT found: returns 'HOLD' (remains on Bullish FVG step)
            - If FVG found: returns 'HOLD' (proceeds to next step)
        """
        if self.analyze(market_data):
            # FVG detected - proceed to next step
            return 'HOLD'
        # FVG not detected - remain on this step
        return 'HOLD'

    def _find_bullish_fvg(self, candles: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Find bullish fair value gap (3-candle pattern).
        
        A bullish FVG occurs when:
        - Candle 1 (C1): First closed candle
        - Candle 2 (C2): Strong bullish candle (gap creator)
        - Candle 3 (C3): Third closed candle
        - Gap: C1 high < C3 low (no touch between wicks)
        - C1 high = bottom of gap
        - C3 low = top of gap
        
        Returns:
            Dictionary with FVG data or None
        """
        max_lookback = self.params['max_candles_lookback']
        min_gap_pct = self.params['min_gap_percentage']
        
        # Search recent candles for FVG pattern
        start_idx = max(0, len(candles) - max_lookback)
        
        for i in range(start_idx, len(candles) - 2):
            candle1 = candles[i]
            candle2 = candles[i + 1]
            candle3 = candles[i + 2]
            
            # Extract price levels from closed candles
            # Using high/low to include wicks as per FVG definition
            c1_high = float(candle1['high'])
            c1_low = float(candle1['low'])
            c2_open = float(candle2['open'])
            c2_close = float(candle2['close'])
            c2_high = float(candle2['high'])
            c3_low = float(candle3['low'])
            c3_high = float(candle3['high'])
            
            # Check for bullish FVG pattern
            # 1. Candle 2 should be bullish (strong upward movement)
            if c2_close <= c2_open:
                continue
            
            # 2. Check if there's a gap (C1 high < C3 low, wicks don't touch)
            # Skip if NO gap exists (c1_high >= c3_low means they touch or overlap)
            if c1_high >= c3_low:
                continue
            
            # 3. Calculate gap size safely
            gap_size = c3_low - c1_high
            # Validate c1_high for safe division (reject zero or negative prices)
            if c1_high <= 0:
                self.logger.warning(f"Invalid c1_high value: {c1_high} at candle index {i}, skipping")
                continue
            
            gap_percentage = (gap_size / c1_high) * 100
            
            # 4. Verify minimum gap size
            if gap_percentage < min_gap_pct:
                continue
            
            # Bullish FVG found
            # FVG zone: bottom = C1 high, top = C3 low
            fvg_data = {
                'low': c1_high,
                'high': c3_low,
                'gap_size': gap_size,
                'gap_percentage': gap_percentage,
                'candle1_idx': i,
                'candle2_idx': i + 1,
                'candle3_idx': i + 2,
                'candles': [candle1, candle2, candle3]
            }
            
            self.logger.debug(f"Bullish FVG: {fvg_data['low']:.4f} - {fvg_data['high']:.4f} ({gap_percentage:.2f}%)")
            return fvg_data
        
        return None

    def is_price_in_fvg(self, current_price: float) -> bool:
        """
        Check if current price is within the FVG zone.
        
        Args:
            current_price: Current market price
            
        Returns:
            True if price is in FVG, False otherwise
        """
        if not self.fvg_zone:
            return False
        
        return self.fvg_zone['low'] <= current_price <= self.fvg_zone['high']

    def check_price_retracement(self, market_data: Dict[str, Any]) -> bool:
        """
        Check if price has retraced into the FVG zone.
        
        Args:
            market_data: Dictionary containing candles
            
        Returns:
            True if price has retraced into FVG, False otherwise
        """
        if not self.fvg_zone:
            return False
        
        if not self.validate_market_data(market_data, ['candles']):
            return False
        
        candles = market_data['candles']
        if not candles:
            return False
        
        # Check recent candles for retracement
        recent_candles = candles[-5:]
        
        for candle in recent_candles:
            low = float(candle['low'])
            high = float(candle['high'])
            close = float(candle['close'])
            
            # Check if price entered FVG zone
            if (low <= self.fvg_zone['high'] and high >= self.fvg_zone['low']):
                # Price touched FVG zone
                if self.fvg_zone['low'] <= close <= self.fvg_zone['high']:
                    # Close inside FVG - strong retracement
                    self.logger.info(f"Price retraced into FVG: close={close:.4f}")
                    return True
        
        return False

    def get_fvg_zone(self) -> Optional[Dict[str, Any]]:
        """
        Get the FVG zone data.
        
        Returns:
            FVG zone dictionary or None
        """
        return self.fvg_zone

    def is_fvg_detected(self) -> bool:
        """
        Check if FVG has been detected.
        
        Returns:
            True if FVG detected, False otherwise
        """
        return self.fvg_detected

    def get_fvg_levels(self) -> Optional[Tuple[float, float]]:
        """
        Get FVG support and resistance levels.
        
        Returns:
            Tuple of (low, high) or None
        """
        if self.fvg_zone:
            return (self.fvg_zone['low'], self.fvg_zone['high'])
        return None

    def reset(self):
        """Reset filter state."""
        self.fvg_detected = False
        self.fvg_zone = None
