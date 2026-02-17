"""
Step 1 Filter - Market Structure Analysis
Identifies overall market structure and liquidity conditions.
"""

from typing import Dict, Any, Optional, List
from filters.base_filter import BaseFilter


class MarketStructureFilter(BaseFilter):
    """
    Step 1: Market Structure Filter.
    
    Analyzes overall market structure to identify:
    - Current trend direction (higher timeframe context)
    - Market liquidity levels
    - Valid trading conditions
    
    This is the first step before looking for downtrend.
    """
    
    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """
        Initialize market structure filter.
        
        Args:
            params: Optional parameters
                - min_volume: Minimum average volume required (default: 1000.0)
                - min_candles: Minimum candles required for analysis (default: 20)
                - structure_lookback: Periods for structure analysis (default: 30)
        """
        default_params = {
            'min_volume': 1000.0,
            'min_candles': 20,
            'structure_lookback': 30
        }
        if params:
            default_params.update(params)
        super().__init__("MarketStructureFilter", default_params)
        
        self.market_structure = None
    
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
    
    def _check_sufficient_liquidity(self, candles: List[Dict[str, float]]) -> bool:
        """
        Check if market has sufficient liquidity for trading.
        
        Args:
            candles: List of candlestick data
            
        Returns:
            True if liquidity is sufficient, False otherwise
        """
        if len(candles) < 10:
            return False
        
        # Calculate average volume
        volumes = [c['volume'] for c in candles[-10:]]
        avg_volume = sum(volumes) / len(volumes)
        
        min_volume = self.params['min_volume']
        
        if avg_volume >= min_volume:
            self.logger.debug(f"Liquidity sufficient: avg volume {avg_volume:.2f} >= {min_volume}")
            return True
        else:
            self.logger.debug(f"Liquidity insufficient: avg volume {avg_volume:.2f} < {min_volume}")
            return False
    
    def _identify_market_structure(self, candles: List[Dict[str, float]]) -> Optional[str]:
        """
        Identify overall market structure.
        
        Args:
            candles: List of candlestick data
            
        Returns:
            Market structure type: 'ranging', 'trending_up', 'trending_down', or None
        """
        lookback = min(self.params['structure_lookback'], len(candles))
        if lookback < 10:
            return None
        
        recent_candles = candles[-lookback:]
        
        # Calculate highest high and lowest low
        highest_high = max(c['high'] for c in recent_candles)
        lowest_low = min(c['low'] for c in recent_candles)
        
        # Calculate price range
        price_range = highest_high - lowest_low
        avg_price = (highest_high + lowest_low) / 2
        range_percent = (price_range / avg_price) * 100
        
        # Check if recent prices are near highs or lows
        recent_price = recent_candles[-1]['close']
        distance_from_high = ((highest_high - recent_price) / price_range) * 100
        distance_from_low = ((recent_price - lowest_low) / price_range) * 100
        
        # Determine structure
        # If price is in middle 40-60% range, likely ranging
        if 40 <= distance_from_low <= 60:
            structure = 'ranging'
        # If price is near highs (top 30%), but overall range is significant
        elif distance_from_low > 70 and range_percent > 2:
            structure = 'trending_up'
        # If price is near lows (bottom 30%)
        elif distance_from_low < 30:
            structure = 'trending_down'
        else:
            structure = 'ranging'
        
        self.logger.debug(
            f"Market structure: {structure} "
            f"(range: {range_percent:.2f}%, distance_from_low: {distance_from_low:.1f}%)"
        )
        
        return structure
    
    def _check_valid_trading_conditions(self, candles: List[Dict[str, float]]) -> bool:
        """
        Check if current market conditions are valid for trading.
        
        Args:
            candles: List of candlestick data
            
        Returns:
            True if conditions are valid, False otherwise
        """
        if len(candles) < 5:
            return False
        
        # Check for abnormal volatility (gap between consecutive candles)
        recent_candles = candles[-5:]
        max_gap_percent = 0
        
        for i in range(1, len(recent_candles)):
            prev_close = recent_candles[i-1]['close']
            curr_open = recent_candles[i]['open']
            gap = abs(curr_open - prev_close)
            gap_percent = (gap / prev_close) * 100
            max_gap_percent = max(max_gap_percent, gap_percent)
        
        # If gap is too large (>5%), might be abnormal conditions
        if max_gap_percent > 5:
            self.logger.warning(f"Abnormal gap detected: {max_gap_percent:.2f}%")
            return False
        
        # Check for sufficient price movement (not flatlined)
        highs = [c['high'] for c in recent_candles]
        lows = [c['low'] for c in recent_candles]
        price_movement = (max(highs) - min(lows)) / min(lows) * 100
        
        if price_movement < 0.1:
            self.logger.debug(f"Insufficient price movement: {price_movement:.2f}%")
            return False
        
        return True
    
    def analyze(self, market_data: Dict[str, Any]) -> bool:
        """
        Analyze market structure and conditions for Step 1.
        
        Args:
            market_data: Dictionary containing klines data
            
        Returns:
            True if market structure is identified and conditions are valid, False otherwise
        """
        if not self.validate_market_data(market_data, ['klines']):
            self.logger.warning("Missing klines data in market_data")
            return False
        
        klines = market_data['klines']
        min_candles = self.params['min_candles']
        
        if not klines or len(klines) < min_candles:
            self.logger.warning(f"Insufficient kline data: {len(klines) if klines else 0} < {min_candles}")
            return False
        
        candles = self._parse_klines(klines)
        
        # Check liquidity
        has_liquidity = self._check_sufficient_liquidity(candles)
        if not has_liquidity:
            self.logger.debug("Insufficient market liquidity")
            return False
        
        # Identify market structure
        structure = self._identify_market_structure(candles)
        if not structure:
            self.logger.debug("Unable to identify market structure")
            return False
        
        self.market_structure = structure
        
        # Check valid trading conditions
        valid_conditions = self._check_valid_trading_conditions(candles)
        if not valid_conditions:
            self.logger.debug("Invalid trading conditions")
            return False
        
        self.logger.info(
            f"Step 1 confirmed: Market structure identified as '{structure}', "
            f"liquidity sufficient, conditions valid"
        )
        
        return True
    
    def get_signal(self, market_data: Dict[str, Any]) -> str:
        """
        Get trading signal from market structure analysis.
        
        Args:
            market_data: Dictionary containing market data
            
        Returns:
            'HOLD' always, as this is just a filter step
        """
        # Market structure filter doesn't generate buy/sell signals
        # It's used by state machine to confirm initial conditions
        return 'HOLD'
    
    def get_market_structure(self) -> Optional[str]:
        """Get the identified market structure."""
        return self.market_structure
