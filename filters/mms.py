"""
MMS Filter - Step 5
Market Structure Shift detection.
"""

from typing import Dict, Any, Optional, List
from filters.base_filter import BaseFilter


class MMSFilter(BaseFilter):
    """
    Market Structure Shift (MMS) detection filter.
    
    Identifies:
    - First higher low after CHOCH
    - Confirmation of structure rotation
    """
    
    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """
        Initialize MMS filter.
        
        Args:
            params: Optional parameters
                - choch_level: Required CHOCH level from previous step
                - confirmation_period: Candles to confirm higher low (default: 3)
        """
        default_params = {
            'choch_level': None,
            'confirmation_period': 3
        }
        if params:
            default_params.update(params)
        super().__init__("MMSFilter", default_params)
        
        self.higher_low = None
    
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
    
    def _find_recent_lows(self, candles: List[Dict[str, float]], count: int = 5) -> List[Dict[str, Any]]:
        """
        Find recent swing lows.
        
        Args:
            candles: List of candlestick data
            count: Number of recent lows to find
            
        Returns:
            List of swing lows
        """
        lows = []
        
        for i in range(len(candles) - 2, 1, -1):
            if (candles[i]['low'] < candles[i-1]['low'] and 
                candles[i]['low'] < candles[i+1]['low']):
                lows.append({
                    'index': i,
                    'price': candles[i]['low'],
                    'timestamp': candles[i]['timestamp']
                })
                if len(lows) >= count:
                    break
        
        return lows
    
    def _detect_higher_low(self, candles: List[Dict[str, float]], choch_level: float) -> Optional[Dict[str, Any]]:
        """
        Detect first higher low after CHOCH.
        
        Args:
            candles: List of candlestick data
            choch_level: CHOCH level from previous step
            
        Returns:
            Higher low info or None
        """
        recent_lows = self._find_recent_lows(candles, count=3)
        
        if len(recent_lows) < 2:
            return None
        
        # Check if most recent low is higher than previous low
        # and both are above CHOCH level
        latest_low = recent_lows[0]
        previous_low = recent_lows[1]
        
        if (latest_low['price'] > previous_low['price'] and 
            latest_low['price'] > choch_level):
            return latest_low
        
        return None
    
    def _confirm_structure_shift(self, candles: List[Dict[str, float]], higher_low: Dict[str, Any]) -> bool:
        """
        Confirm that market structure has shifted to bullish.
        
        Args:
            candles: List of candlestick data
            higher_low: Higher low information
            
        Returns:
            True if structure shift confirmed, False otherwise
        """
        if not higher_low:
            return False
        
        hl_index = higher_low['index']
        hl_price = higher_low['price']
        
        # Check subsequent candles stay above higher low
        confirmation_count = 0
        
        for i in range(hl_index + 1, len(candles)):
            if candles[i]['low'] > hl_price:
                confirmation_count += 1
            else:
                # If price drops back below higher low, structure not confirmed
                return False
            
            if confirmation_count >= self.params['confirmation_period']:
                return True
        
        return confirmation_count >= self.params['confirmation_period']
    
    def analyze(self, market_data: Dict[str, Any]) -> bool:
        """
        Analyze market data for MMS conditions.
        
        Args:
            market_data: Dictionary containing klines data and choch_level
            
        Returns:
            True if MMS is formed, False otherwise
        """
        if not self.validate_market_data(market_data, ['klines']):
            self.logger.warning("Missing klines data in market_data")
            return False
        
        # Get CHOCH level from params or market_data
        choch_level = market_data.get('choch_level') or self.params.get('choch_level')
        if not choch_level:
            self.logger.warning("CHOCH level not provided, cannot detect MMS")
            return False
        
        klines = market_data['klines']
        if not klines or len(klines) < 15:
            self.logger.warning("Insufficient kline data for analysis")
            return False
        
        candles = self._parse_klines(klines)
        
        # Detect higher low
        higher_low = self._detect_higher_low(candles, choch_level)
        
        if not higher_low:
            self.logger.debug("No higher low detected after CHOCH")
            return False
        
        self.higher_low = higher_low
        self.logger.debug(f"Higher low detected at price {higher_low['price']:.2f}")
        
        # Confirm structure shift
        is_confirmed = self._confirm_structure_shift(candles, higher_low)
        
        if not is_confirmed:
            self.logger.debug("Market structure shift not confirmed")
            return False
        
        self.logger.info(
            f"MMS confirmed: Higher low at {higher_low['price']:.2f}, "
            f"above CHOCH level {choch_level:.2f}"
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
    
    def get_higher_low(self) -> Optional[Dict[str, Any]]:
        """Get the identified higher low."""
        return self.higher_low
