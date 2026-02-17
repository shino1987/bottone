"""
Bullish FVG Filter - Step 6
Fair Value Gap detection for bullish setups.
"""

from typing import Dict, Any, Optional, List
from filters.base_filter import BaseFilter


class BullishFVGFilter(BaseFilter):
    """
    Bullish Fair Value Gap (FVG) detection filter.
    
    Identifies:
    - FVG bullish (gap between 3 candles)
    - Candle 1 and candle 3 don't overlap
    - Tracks retracement price into FVG
    """
    
    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """
        Initialize Bullish FVG filter.
        
        Args:
            params: Optional parameters
                - min_gap_percent: Minimum gap size as % of price (default: 0.1)
                - lookback: Number of recent candles to check (default: 20)
        """
        default_params = {
            'min_gap_percent': 0.1,
            'lookback': 20
        }
        if params:
            default_params.update(params)
        super().__init__("BullishFVGFilter", default_params)
        
        self.fvg_zone = None
    
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
    
    def _detect_bullish_fvg(self, candles: List[Dict[str, float]]) -> Optional[Dict[str, Any]]:
        """
        Detect bullish Fair Value Gap.
        
        A bullish FVG occurs when:
        - Candle 1 (before): bearish or neutral
        - Candle 2 (middle): strong bullish move
        - Candle 3 (after): bullish continuation
        - Gap: high of candle 1 < low of candle 3 (no overlap)
        
        Args:
            candles: List of candlestick data
            
        Returns:
            FVG zone info or None
        """
        lookback = self.params['lookback']
        min_gap_percent = self.params['min_gap_percent']
        
        # Need at least 3 candles
        if len(candles) < 3:
            return None
        
        # Check recent candles for FVG pattern
        start_idx = max(0, len(candles) - lookback)
        
        for i in range(start_idx, len(candles) - 2):
            candle1 = candles[i]      # Before
            candle2 = candles[i + 1]  # Middle
            candle3 = candles[i + 2]  # After
            
            # Check for bullish pattern
            # Candle 2 should be bullish
            if candle2['close'] <= candle2['open']:
                continue
            
            # Check for gap: high of candle 1 < low of candle 3
            if candle1['high'] >= candle3['low']:
                continue
            
            # Calculate gap size
            gap_size = candle3['low'] - candle1['high']
            gap_percent = (gap_size / candle1['close']) * 100
            
            if gap_percent < min_gap_percent:
                continue
            
            # Found bullish FVG
            fvg_zone = {
                'index': i,
                'low': candle1['high'],      # Bottom of FVG
                'high': candle3['low'],      # Top of FVG
                'mid': (candle1['high'] + candle3['low']) / 2,
                'gap_size': gap_size,
                'gap_percent': gap_percent,
                'timestamp': candle2['timestamp']
            }
            
            self.logger.debug(
                f"Bullish FVG detected at index {i}: "
                f"[{fvg_zone['low']:.2f} - {fvg_zone['high']:.2f}], "
                f"gap {gap_percent:.2f}%"
            )
            
            return fvg_zone
        
        return None
    
    def _check_price_in_fvg(self, current_price: float, fvg_zone: Dict[str, Any]) -> bool:
        """
        Check if current price is within FVG zone.
        
        Args:
            current_price: Current market price
            fvg_zone: FVG zone information
            
        Returns:
            True if price is in FVG, False otherwise
        """
        if not fvg_zone:
            return False
        
        return fvg_zone['low'] <= current_price <= fvg_zone['high']
    
    def analyze(self, market_data: Dict[str, Any]) -> bool:
        """
        Analyze market data for Bullish FVG.
        
        Args:
            market_data: Dictionary containing klines data
            
        Returns:
            True if bullish FVG is formed, False otherwise
        """
        if not self.validate_market_data(market_data, ['klines']):
            self.logger.warning("Missing klines data in market_data")
            return False
        
        klines = market_data['klines']
        if not klines or len(klines) < 5:
            self.logger.warning("Insufficient kline data for analysis")
            return False
        
        candles = self._parse_klines(klines)
        
        # Detect bullish FVG
        fvg_zone = self._detect_bullish_fvg(candles)
        
        if not fvg_zone:
            self.logger.debug("No bullish FVG detected")
            return False
        
        self.fvg_zone = fvg_zone
        
        self.logger.info(
            f"Bullish FVG formed: "
            f"Zone [{fvg_zone['low']:.2f} - {fvg_zone['high']:.2f}], "
            f"gap size {fvg_zone['gap_size']:.2f} ({fvg_zone['gap_percent']:.2f}%)"
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
    
    def get_fvg_zone(self) -> Optional[Dict[str, Any]]:
        """Get the identified FVG zone."""
        return self.fvg_zone
    
    def is_price_in_fvg(self, price: float) -> bool:
        """
        Check if given price is within the FVG zone.
        
        Args:
            price: Price to check
            
        Returns:
            True if price is in FVG zone, False otherwise
        """
        return self._check_price_in_fvg(price, self.fvg_zone)
