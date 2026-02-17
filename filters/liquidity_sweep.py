"""
Liquidity Sweep Filter - Step 3
Finds liquidity sweep + demand zone.
"""

from typing import Dict, Any, Optional, List
from filters.base_filter import BaseFilter


class LiquiditySweepFilter(BaseFilter):
    """
    Liquidity sweep detection filter.
    
    Identifies:
    - Previous swing low (buyside liquidity)
    - Break above swing low (liquidity sweep)
    - Demand zone (accumulation with volume)
    """
    
    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """
        Initialize liquidity sweep filter.
        
        Args:
            params: Optional parameters
                - swing_lookback: Periods to look back for swing low (default: 10)
                - volume_threshold: Volume threshold multiplier (default: 1.5)
                - sweep_confirmation: Candles to confirm sweep (default: 2)
        """
        default_params = {
            'swing_lookback': 10,
            'volume_threshold': 1.5,
            'sweep_confirmation': 2
        }
        if params:
            default_params.update(params)
        super().__init__("LiquiditySweepFilter", default_params)
        
        self.swing_low = None
        self.demand_zone = None
    
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
    
    def _find_swing_low(self, candles: List[Dict[str, float]], lookback: int) -> Optional[Dict[str, Any]]:
        """
        Find the most recent swing low.
        
        Args:
            candles: List of candlestick data
            lookback: Number of periods to look back
            
        Returns:
            Dictionary with swing low info or None
        """
        if len(candles) < lookback + 2:
            return None
        
        # Calculate search range
        # Start searching from 3 candles before the end (to have context)
        start_search_idx = len(candles) - 3
        # Search back to the lookback limit, but not before index 1
        end_search_idx = max(1, len(candles) - lookback - 3)
        
        # Look for local minimum (low lower than surrounding candles)
        for i in range(start_search_idx, end_search_idx, -1):
            # Ensure we can safely access i-1 and i+1
            if 0 < i < len(candles) - 1:
                if (candles[i]['low'] < candles[i-1]['low'] and 
                    candles[i]['low'] < candles[i+1]['low']):
                    return {
                        'index': i,
                        'price': candles[i]['low'],
                        'timestamp': candles[i]['timestamp']
                    }
        
        return None
    
    def _detect_sweep(self, candles: List[Dict[str, float]], swing_low: Dict[str, Any]) -> bool:
        """
        Detect if price swept above the swing low.
        
        Args:
            candles: List of candlestick data
            swing_low: Swing low information
            
        Returns:
            True if sweep detected, False otherwise
        """
        if not swing_low:
            return False
        
        swing_index = swing_low['index']
        swing_price = swing_low['price']
        
        # Check if any subsequent candles broke above swing low
        for i in range(swing_index + 1, len(candles)):
            if candles[i]['high'] > swing_price:
                # Confirm with closing above
                confirmation_count = 0
                for j in range(i, min(i + self.params['sweep_confirmation'], len(candles))):
                    if candles[j]['close'] > swing_price:
                        confirmation_count += 1
                
                if confirmation_count >= self.params['sweep_confirmation']:
                    self.logger.debug(f"Sweep detected at index {i}, price {candles[i]['high']}")
                    return True
        
        return False
    
    def _identify_demand_zone(self, candles: List[Dict[str, float]], swing_low: Dict[str, Any]) -> Optional[Dict[str, float]]:
        """
        Identify demand zone near swing low with volume accumulation.
        
        Args:
            candles: List of candlestick data
            swing_low: Swing low information
            
        Returns:
            Demand zone price range or None
        """
        if not swing_low:
            return None
        
        swing_index = swing_low['index']
        
        # Calculate average volume
        volumes = [c['volume'] for c in candles]
        avg_volume = sum(volumes) / len(volumes)
        volume_threshold = avg_volume * self.params['volume_threshold']
        
        # Look for high volume candles near swing low
        demand_start = None
        demand_end = None
        
        # Check 5 candles before and after swing low
        start_idx = max(0, swing_index - 5)
        end_idx = min(len(candles), swing_index + 5)
        
        for i in range(start_idx, end_idx):
            if candles[i]['volume'] > volume_threshold:
                if demand_start is None:
                    demand_start = candles[i]['low']
                    demand_end = candles[i]['high']
                else:
                    demand_start = min(demand_start, candles[i]['low'])
                    demand_end = max(demand_end, candles[i]['high'])
        
        if demand_start and demand_end:
            return {
                'low': demand_start,
                'high': demand_end,
                'mid': (demand_start + demand_end) / 2
            }
        
        return None
    
    def analyze(self, market_data: Dict[str, Any]) -> bool:
        """
        Analyze market data for liquidity sweep and demand zone.
        
        Args:
            market_data: Dictionary containing klines data
            
        Returns:
            True if sweep + demand zone found, False otherwise
        """
        if not self.validate_market_data(market_data, ['klines']):
            self.logger.warning("Missing klines data in market_data")
            return False
        
        klines = market_data['klines']
        if not klines or len(klines) < 20:
            self.logger.warning("Insufficient kline data for analysis")
            return False
        
        candles = self._parse_klines(klines)
        
        # Find swing low
        lookback = self.params['swing_lookback']
        swing_low = self._find_swing_low(candles, lookback)
        
        if not swing_low:
            self.logger.debug("No swing low found")
            return False
        
        self.swing_low = swing_low
        self.logger.debug(f"Swing low found at price {swing_low['price']}")
        
        # Detect sweep
        has_sweep = self._detect_sweep(candles, swing_low)
        if not has_sweep:
            self.logger.debug("No liquidity sweep detected")
            return False
        
        # Identify demand zone
        demand_zone = self._identify_demand_zone(candles, swing_low)
        if not demand_zone:
            self.logger.debug("No demand zone identified")
            return False
        
        self.demand_zone = demand_zone
        self.logger.info(
            f"Liquidity sweep + demand zone found: "
            f"Sweep at {swing_low['price']:.2f}, "
            f"Demand zone [{demand_zone['low']:.2f} - {demand_zone['high']:.2f}]"
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
    
    def get_swing_low(self) -> Optional[Dict[str, Any]]:
        """Get the identified swing low."""
        return self.swing_low
    
    def get_demand_zone(self) -> Optional[Dict[str, float]]:
        """Get the identified demand zone."""
        return self.demand_zone
