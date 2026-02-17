"""
Downtrend Filter - Step 2
Identifies downtrend on 15min timeframe.
"""

from typing import Dict, Any, Optional, List
from filters.base_filter import BaseFilter


class DowntrendFilter(BaseFilter):
    """
    Downtrend detection filter.
    
    Identifies downtrend based on:
    - At least 2-3 consecutive lower lows
    - At least 2-3 consecutive lower highs
    - Negative slope of moving average
    """
    
    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """
        Initialize downtrend filter.
        
        Args:
            params: Optional parameters
                - min_lower_lows: Minimum consecutive lower lows (default: 2)
                - min_lower_highs: Minimum consecutive lower highs (default: 2)
                - ma_period: Moving average period (default: 20)
        """
        default_params = {
            'min_lower_lows': 2,
            'min_lower_highs': 2,
            'ma_period': 20
        }
        if params:
            default_params.update(params)
        super().__init__("DowntrendFilter", default_params)
    
    def _parse_klines(self, klines: List) -> List[Dict[str, float]]:
        """
        Parse raw kline data into structured format.
        
        Args:
            klines: Raw kline data from Binance API
            
        Returns:
            List of candlestick dictionaries with open, high, low, close, volume
        """
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
    
    def _calculate_ma(self, candles: List[Dict[str, float]], period: int) -> Optional[float]:
        """
        Calculate simple moving average of closing prices.
        
        Args:
            candles: List of candlestick data
            period: MA period
            
        Returns:
            Moving average value or None if insufficient data
        """
        if len(candles) < period:
            return None
        
        closes = [c['close'] for c in candles[-period:]]
        return sum(closes) / period
    
    def _detect_lower_lows(self, candles: List[Dict[str, float]]) -> int:
        """
        Detect consecutive lower lows.
        
        Args:
            candles: List of candlestick data
            
        Returns:
            Count of consecutive lower lows
        """
        if len(candles) < 2:
            return 0
        
        count = 0
        for i in range(len(candles) - 1, 0, -1):
            if candles[i]['low'] < candles[i-1]['low']:
                count += 1
            else:
                break
        
        return count
    
    def _detect_lower_highs(self, candles: List[Dict[str, float]]) -> int:
        """
        Detect consecutive lower highs.
        
        Args:
            candles: List of candlestick data
            
        Returns:
            Count of consecutive lower highs
        """
        if len(candles) < 2:
            return 0
        
        count = 0
        for i in range(len(candles) - 1, 0, -1):
            if candles[i]['high'] < candles[i-1]['high']:
                count += 1
            else:
                break
        
        return count
    
    def _check_ma_slope(self, candles: List[Dict[str, float]], period: int) -> bool:
        """
        Check if moving average has negative slope.
        
        Args:
            candles: List of candlestick data
            period: MA period
            
        Returns:
            True if MA slope is negative, False otherwise
        """
        if len(candles) < period + 5:
            return False
        
        # Calculate MA for current and 5 periods ago
        ma_current = self._calculate_ma(candles, period)
        ma_past = self._calculate_ma(candles[:-5], period)
        
        if ma_current is None or ma_past is None:
            return False
        
        return ma_current < ma_past
    
    def analyze(self, market_data: Dict[str, Any]) -> bool:
        """
        Analyze market data for downtrend conditions.
        
        Args:
            market_data: Dictionary containing klines data
            
        Returns:
            True if downtrend is confirmed, False otherwise
        """
        if not self.validate_market_data(market_data, ['klines']):
            self.logger.warning("Missing klines data in market_data")
            return False
        
        klines = market_data['klines']
        if not klines or len(klines) < 10:
            self.logger.warning("Insufficient kline data for analysis")
            return False
        
        candles = self._parse_klines(klines)
        
        # Check for lower lows
        lower_lows = self._detect_lower_lows(candles)
        self.logger.debug(f"Detected {lower_lows} consecutive lower lows")
        
        # Check for lower highs
        lower_highs = self._detect_lower_highs(candles)
        self.logger.debug(f"Detected {lower_highs} consecutive lower highs")
        
        # Check MA slope
        ma_period = self.params['ma_period']
        ma_negative = self._check_ma_slope(candles, ma_period)
        self.logger.debug(f"MA slope negative: {ma_negative}")
        
        # Confirm downtrend
        min_lower_lows = self.params['min_lower_lows']
        min_lower_highs = self.params['min_lower_highs']
        
        is_downtrend = (
            lower_lows >= min_lower_lows and
            lower_highs >= min_lower_highs and
            ma_negative
        )
        
        if is_downtrend:
            self.logger.info(f"Downtrend confirmed: LL={lower_lows}, LH={lower_highs}, MA-={ma_negative}")
        
        return is_downtrend
    
    def get_signal(self, market_data: Dict[str, Any]) -> str:
        """
        Get trading signal from downtrend analysis.
        
        Args:
            market_data: Dictionary containing market data
            
        Returns:
            'HOLD' always, as this is just a filter step
        """
        # Downtrend filter doesn't generate buy/sell signals
        # It's used by state machine to confirm conditions
        return 'HOLD'
