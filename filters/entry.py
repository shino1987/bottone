"""
Entry Filter - Step 7
Entry logic with SL/TP calculation.
"""

from typing import Dict, Any, Optional, List
from filters.base_filter import BaseFilter


class EntryFilter(BaseFilter):
    """
    Entry logic filter.
    
    Monitors:
    - Price retracement into FVG
    - Candle closing inside FVG
    - Triggers LONG entry
    - Calculates SL and TP automatically
    """
    
    # Pip conversion factor (0.0001 for most forex pairs, 0.01 for JPY pairs)
    # This should be adjusted based on instrument
    PIP_CONVERSION_FACTOR = 0.0001
    
    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """
        Initialize Entry filter.
        
        Args:
            params: Optional parameters
                - fvg_zone: Required FVG zone from previous step
                - risk_reward_ratio: Risk/reward ratio (default: 3.0)
                - sl_offset_pips: SL offset below FVG in pips (default: 5)
                - pip_conversion: Pip conversion factor (default: 0.0001)
        """
        default_params = {
            'fvg_zone': None,
            'risk_reward_ratio': 3.0,
            'sl_offset_pips': 5,
            'pip_conversion': self.PIP_CONVERSION_FACTOR
        }
        if params:
            default_params.update(params)
        super().__init__("EntryFilter", default_params)
        
        self.entry_price = None
        self.stop_loss = None
        self.take_profit = None
        self.entry_triggered = False
    
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
    
    def _check_retracement_into_fvg(self, candles: List[Dict[str, float]], fvg_zone: Dict[str, Any]) -> bool:
        """
        Check if price has retraced into FVG zone.
        
        Args:
            candles: List of candlestick data
            fvg_zone: FVG zone information
            
        Returns:
            True if price is in FVG, False otherwise
        """
        if not fvg_zone or len(candles) == 0:
            return False
        
        latest_candle = candles[-1]
        
        # Check if latest candle closes inside FVG
        fvg_low = fvg_zone['low']
        fvg_high = fvg_zone['high']
        
        is_in_fvg = fvg_low <= latest_candle['close'] <= fvg_high
        
        if is_in_fvg:
            self.logger.debug(
                f"Price retraced into FVG: close {latest_candle['close']:.2f} "
                f"in zone [{fvg_low:.2f} - {fvg_high:.2f}]"
            )
        
        return is_in_fvg
    
    def _calculate_stop_loss(self, fvg_zone: Dict[str, Any]) -> float:
        """
        Calculate stop loss below FVG.
        
        Args:
            fvg_zone: FVG zone information
            
        Returns:
            Stop loss price
        """
        # Place SL below FVG with offset
        pip_conversion = self.params.get('pip_conversion', self.PIP_CONVERSION_FACTOR)
        sl_offset = self.params['sl_offset_pips'] * pip_conversion
        stop_loss = fvg_zone['low'] - sl_offset
        
        return stop_loss
    
    def _calculate_take_profit(self, entry_price: float, stop_loss: float, risk_reward: float) -> float:
        """
        Calculate take profit based on risk/reward ratio.
        
        Args:
            entry_price: Entry price
            stop_loss: Stop loss price
            risk_reward: Risk/reward ratio
            
        Returns:
            Take profit price
        """
        risk = entry_price - stop_loss
        reward = risk * risk_reward
        take_profit = entry_price + reward
        
        return take_profit
    
    def analyze(self, market_data: Dict[str, Any]) -> bool:
        """
        Analyze market data for entry conditions.
        
        Args:
            market_data: Dictionary containing klines data and fvg_zone
            
        Returns:
            True if entry is triggered, False otherwise
        """
        if not self.validate_market_data(market_data, ['klines']):
            self.logger.warning("Missing klines data in market_data")
            return False
        
        # Get FVG zone from params or market_data
        fvg_zone = market_data.get('fvg_zone') or self.params.get('fvg_zone')
        if not fvg_zone:
            self.logger.warning("FVG zone not provided, cannot trigger entry")
            return False
        
        klines = market_data['klines']
        if not klines or len(klines) == 0:
            self.logger.warning("No kline data for analysis")
            return False
        
        candles = self._parse_klines(klines)
        
        # Check if price retraced into FVG
        is_in_fvg = self._check_retracement_into_fvg(candles, fvg_zone)
        
        if not is_in_fvg:
            self.logger.debug("Price not in FVG yet")
            return False
        
        # Entry triggered!
        latest_candle = candles[-1]
        self.entry_price = latest_candle['close']
        self.stop_loss = self._calculate_stop_loss(fvg_zone)
        self.take_profit = self._calculate_take_profit(
            self.entry_price,
            self.stop_loss,
            self.params['risk_reward_ratio']
        )
        self.entry_triggered = True
        
        self.logger.info(
            f"ENTRY TRIGGERED: "
            f"Entry: {self.entry_price:.2f}, "
            f"SL: {self.stop_loss:.2f}, "
            f"TP: {self.take_profit:.2f}, "
            f"RR: {self.params['risk_reward_ratio']:.1f}"
        )
        
        return True
    
    def get_signal(self, market_data: Dict[str, Any]) -> str:
        """
        Get trading signal.
        
        Args:
            market_data: Dictionary containing market data
            
        Returns:
            'BUY' if entry triggered, 'HOLD' otherwise
        """
        if self.analyze(market_data):
            return 'BUY'
        return 'HOLD'
    
    def get_entry_details(self) -> Optional[Dict[str, float]]:
        """
        Get entry details including SL and TP.
        
        Returns:
            Dictionary with entry, SL, and TP prices
        """
        if not self.entry_triggered:
            return None
        
        return {
            'entry': self.entry_price,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'risk_reward': self.params['risk_reward_ratio']
        }
    
    def reset(self):
        """Reset entry state."""
        self.entry_price = None
        self.stop_loss = None
        self.take_profit = None
        self.entry_triggered = False
