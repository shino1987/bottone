"""
CHOCH Filter - Step 4
Change of Character detection.
"""

from typing import Dict, Any, Optional, List
from filters.base_filter import BaseFilter


class CHOCHFilter(BaseFilter):
    """
    Change of Character (CHOCH) detection filter.
    
    Monitors for:
    - Market structure break
    - Trend rotation
    - Candle closing above last swing low
    """
    
    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """
        Initialize CHOCH filter.
        
        Args:
            params: Optional parameters
                - lookback_period: Periods to look back for structure (default: 20)
                - confirmation_candles: Candles to confirm CHOCH (default: 1)
        """
        default_params = {
            'lookback_period': 20,
            'confirmation_candles': 1
        }
        if params:
            default_params.update(params)
        super().__init__("CHOCHFilter", default_params)
        
        self.choch_level = None
    
    def _parse_klines(self, klines: List) -> List[Dict[str, float]]:
        """Parse raw kline data into structured format."""
        candles = []
        for kline in klines:
            candles.append({
                'timestamp': kline[0],
                'open': float(kline[1]),
                'high': float(kline[2]),
                'low': float(kline[3]),
                'close': float(kline[4]),
                'volume': float(kline[5])
            })
        return candles
    
    def _find_last_swing_low(self, candles: List[Dict[str, float]], lookback: int) -> Optional[Dict[str, Any]]:
        """
        Find the last significant swing low.
        
        Args:
            candles: List of candlestick data
            lookback: Number of periods to look back
            
        Returns:
            Dictionary with swing low info or None
        """
        if len(candles) < lookback + 2:
            return None
        
        # Find local minimum within lookback period
        swing_lows = []
        for i in range(len(candles) - lookback, len(candles) - 2):
            if i > 0 and i < len(candles) - 1:
                if (candles[i]['low'] < candles[i-1]['low'] and 
                    candles[i]['low'] < candles[i+1]['low']):
                    swing_lows.append({
                        'index': i,
                        'price': candles[i]['low'],
                        'timestamp': candles[i]['timestamp']
                    })
        
        # Return the most recent swing low
        if swing_lows:
            return swing_lows[-1]
        
        return None
    
    def _detect_structure_break(self, candles: List[Dict[str, float]], swing_low: Dict[str, Any]) -> bool:
        """
        Detect if market structure has broken (CHOCH).
        
        Args:
            candles: List of candlestick data
            swing_low: Last swing low information
            
        Returns:
            True if CHOCH detected, False otherwise
        """
        if not swing_low:
            return False
        
        swing_price = swing_low['price']
        swing_index = swing_low['index']
        
        # Look for candle closing above swing low (structure break)
        confirmation_count = 0
        choch_detected = False
        
        for i in range(swing_index + 1, len(candles)):
            if candles[i]['close'] > swing_price:
                confirmation_count += 1
                if confirmation_count >= self.params['confirmation_candles']:
                    choch_detected = True
                    self.choch_level = swing_price
                    self.logger.debug(
                        f"CHOCH detected at candle {i}, "
                        f"close {candles[i]['close']:.2f} > swing low {swing_price:.2f}"
                    )
                    break
            else:
                confirmation_count = 0
        
        return choch_detected
    
    def _check_trend_rotation(self, candles: List[Dict[str, float]]) -> bool:
        """
        Check if trend is rotating from bearish to bullish.
        
        Args:
            candles: List of candlestick data
            
        Returns:
            True if rotation detected, False otherwise
        """
        if len(candles) < 10:
            return False
        
        # Check recent price action
        recent_candles = candles[-10:]
        
        # Count bullish vs bearish candles
        bullish_count = sum(1 for c in recent_candles if c['close'] > c['open'])
        bearish_count = sum(1 for c in recent_candles if c['close'] < c['open'])
        
        # Rotation if more bullish candles recently
        return bullish_count > bearish_count
    
    def analyze(self, market_data: Dict[str, Any]) -> bool:
        """
        Analyze market data for CHOCH conditions.
        
        Args:
            market_data: Dictionary containing klines data
            
        Returns:
            True if CHOCH is verified, False otherwise
        """
        if not self.validate_market_data(market_data, ['klines']):
            self.logger.warning("Missing klines data in market_data")
            return False
        
        klines = market_data['klines']
        if not klines or len(klines) < 25:
            self.logger.warning("Insufficient kline data for analysis")
            return False
        
        candles = self._parse_klines(klines)
        
        # Find last swing low
        lookback = self.params['lookback_period']
        swing_low = self._find_last_swing_low(candles, lookback)
        
        if not swing_low:
            self.logger.debug("No swing low found for CHOCH detection")
            return False
        
        self.logger.debug(f"Analyzing CHOCH with swing low at {swing_low['price']:.2f}")
        
        # Detect structure break
        has_structure_break = self._detect_structure_break(candles, swing_low)
        if not has_structure_break:
            self.logger.debug("No structure break detected")
            return False
        
        # Check for trend rotation
        has_rotation = self._check_trend_rotation(candles)
        if not has_rotation:
            self.logger.debug("No trend rotation detected")
            return False
        
        self.logger.info(
            f"CHOCH verified: Structure break at {self.choch_level:.2f}, "
            f"trend rotation confirmed"
        )
        
        return True
    
    def get_signal(self, market_data: Dict[str, Any]) -> str:
        """
        Get trading signal.
        
        Args:
            market_data: Dictionary containing market data
            
        Returns:
            'HOLD' always, as this is just a filter step
        """
        return 'HOLD'
    
    def get_choch_level(self) -> Optional[float]:
        """Get the CHOCH level (structure break price)."""
        return self.choch_level
