"""
Step 3: Liquidity Sweep Detection Filter
Identifies liquidity sweep above previous swing low with demand zone formation.
"""

from typing import Dict, Any, Optional, List, Tuple
import logging
from filters.base_filter import BaseFilter


class LiquiditySweepFilter(BaseFilter):
    """
    Step 3 - Liquidity Sweep Detection
    - Identify previous swing low (buyside liquidity)
    - Find break above (liquidity sweep)
    - Identify demand zone (volume accumulation)
    - Return TRUE when sweep + demand found
    """

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """Initialize liquidity sweep filter with parameters."""
        default_params = {
            'sweep_threshold': 0.1,  # 0.1% above swing low to confirm sweep
            'volume_multiplier': 1.5,  # 1.5x average volume for demand zone
            'lookback_period': 20,  # Candles to look back for swing lows
            'demand_zone_candles': 3,  # Number of candles for demand zone
        }
        if params:
            default_params.update(params)
        super().__init__("LiquiditySweep", default_params)
        
        # Store detected sweep data
        self.last_swing_low = None
        self.sweep_detected = False
        self.demand_zone = None

    def analyze(self, market_data: Dict[str, Any]) -> bool:
        """
        Analyze market data for liquidity sweep pattern.
        
        Args:
            market_data: Dictionary containing:
                - candles: List of OHLCV candles
                
        Returns:
            True if liquidity sweep with demand zone is detected, False otherwise
        """
        if not self.validate_market_data(market_data, ['candles']):
            return False

        candles = market_data['candles']
        if len(candles) < 30:
            self.logger.warning("Insufficient candles for liquidity sweep analysis")
            return False

        # Find previous swing low
        swing_low_data = self._find_swing_low(candles)
        if not swing_low_data:
            self.logger.debug("No swing low found")
            return False
        
        self.last_swing_low = swing_low_data
        
        # Check for liquidity sweep (break above swing low)
        sweep_detected = self._check_liquidity_sweep(candles, swing_low_data)
        if not sweep_detected:
            self.logger.debug("No liquidity sweep detected")
            return False
        
        self.sweep_detected = True
        
        # Identify demand zone
        demand_zone = self._identify_demand_zone(candles)
        if not demand_zone:
            self.logger.debug("No demand zone found after sweep")
            return False
        
        self.demand_zone = demand_zone
        
        self.logger.info(f"Liquidity sweep confirmed at {swing_low_data['price']:.4f} with demand zone")
        return True

    def get_signal(self, market_data: Dict[str, Any]) -> str:
        """
        Get signal from liquidity sweep filter.
        
        Args:
            market_data: Dictionary containing market data
            
        Returns:
            'HOLD' - This is a validation filter
        """
        if self.analyze(market_data):
            return 'HOLD'  # Sweep detected, continue to next step
        return 'HOLD'

    def _find_swing_low(self, candles: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Find the most recent swing low (buyside liquidity).
        
        Returns:
            Dictionary with swing low data or None
        """
        lookback = self.params['lookback_period']
        window = 2  # Window for local minima detection
        
        recent_candles = candles[-(lookback + window * 2):]
        
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
                return {
                    'price': current_low,
                    'index': i,
                    'candle': recent_candles[i]
                }
        
        return None

    def _check_liquidity_sweep(self, candles: List[Dict[str, Any]], 
                               swing_low_data: Dict[str, Any]) -> bool:
        """
        Check if price has swept above the swing low.
        
        Args:
            candles: List of candles
            swing_low_data: Swing low information
            
        Returns:
            True if sweep detected, False otherwise
        """
        threshold = self.params['sweep_threshold']
        swing_low_price = swing_low_data['price']
        sweep_target = swing_low_price * (1 + threshold / 100)
        
        # Check recent candles for sweep
        recent_candles = candles[-10:]
        
        for candle in recent_candles:
            high = float(candle['high'])
            close = float(candle['close'])
            
            # Sweep occurs when price breaks above swing low and closes above
            if high >= sweep_target and close > swing_low_price:
                self.logger.debug(f"Liquidity sweep detected: high={high:.4f}, target={sweep_target:.4f}")
                return True
        
        return False

    def _identify_demand_zone(self, candles: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Identify demand zone with volume accumulation.
        
        Returns:
            Dictionary with demand zone data or None
        """
        volume_multiplier = self.params['volume_multiplier']
        zone_candles = self.params['demand_zone_candles']
        
        # Calculate average volume
        recent_candles = candles[-20:]
        avg_volume = sum(float(c.get('volume', 0)) for c in recent_candles) / len(recent_candles)
        
        # Look for accumulation zone in last several candles
        for i in range(len(candles) - zone_candles, len(candles)):
            if i < 0:
                continue
            
            zone_slice = candles[i:i+zone_candles]
            if len(zone_slice) < zone_candles:
                continue
            
            # Check if volume is elevated in this zone
            zone_volume = sum(float(c.get('volume', 0)) for c in zone_slice) / len(zone_slice)
            
            if zone_volume >= avg_volume * volume_multiplier:
                # Found demand zone
                low = min(float(c['low']) for c in zone_slice)
                high = max(float(c['high']) for c in zone_slice)
                
                self.logger.debug(f"Demand zone found: {low:.4f} - {high:.4f}, volume: {zone_volume:.2f}")
                
                return {
                    'low': low,
                    'high': high,
                    'volume': zone_volume,
                    'candles': zone_slice
                }
        
        return None

    def get_demand_zone(self) -> Optional[Dict[str, Any]]:
        """
        Get the identified demand zone.
        
        Returns:
            Demand zone data or None
        """
        return self.demand_zone

    def get_sweep_data(self) -> Optional[Dict[str, Any]]:
        """
        Get sweep detection data.
        
        Returns:
            Dictionary with sweep data or None
        """
        if self.sweep_detected and self.last_swing_low:
            return {
                'swing_low': self.last_swing_low,
                'demand_zone': self.demand_zone
            }
        return None

    def reset(self):
        """Reset filter state."""
        self.last_swing_low = None
        self.sweep_detected = False
        self.demand_zone = None
