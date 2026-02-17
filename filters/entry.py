"""
Step 7: Entry Logic Filter
Monitors price retracement into FVG and calculates entry, SL, and TP.
"""

from typing import Dict, Any, Optional, Tuple
import logging
from filters.base_filter import BaseFilter


class EntryFilter(BaseFilter):
    """
    Step 7 - Entry Logic
    - Monitor price retracing into FVG
    - Candle close inside FVG
    - Calculate SL below FVG (5 pips)
    - Calculate TP with 1:3 risk/reward
    - Return TRUE and trigger LONG entry
    """

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """Initialize Entry filter with parameters."""
        default_params = {
            'sl_offset_pips': 5,  # SL offset below FVG in pips
            'risk_reward_ratio': 3.0,  # 1:3 risk/reward
            'risk_percent': 2.0,  # 2% risk per trade
            'pip_value': 0.0001,  # Pip value (default for most pairs)
        }
        if params:
            default_params.update(params)
        super().__init__("Entry", default_params)
        
        self.entry_triggered = False
        self.entry_data = None

    def analyze(self, market_data: Dict[str, Any]) -> bool:
        """
        Analyze market data for entry conditions.
        
        Args:
            market_data: Dictionary containing:
                - candles: List of OHLCV candles
                - fvg_zone: FVG zone data from previous step
                - account_balance: Account balance for position sizing
                
        Returns:
            True if entry conditions are met, False otherwise
        """
        if not self.validate_market_data(market_data, ['candles']):
            return False

        candles = market_data['candles']
        if len(candles) < 5:
            self.logger.warning("Insufficient candles for entry analysis")
            return False

        # Get FVG zone from market data
        fvg_zone = market_data.get('fvg_zone')
        if not fvg_zone:
            self.logger.debug("No FVG zone provided")
            return False

        # Check if price has retraced into FVG
        last_candle = candles[-1]
        retracement = self._check_retracement(last_candle, fvg_zone)
        
        if not retracement:
            self.logger.debug("Price not in FVG zone")
            return False

        # Calculate entry parameters
        entry_price = float(last_candle['close'])
        sl_price = self._calculate_stop_loss(fvg_zone)
        tp_price = self._calculate_take_profit(entry_price, sl_price)
        
        # Calculate position size
        account_balance = market_data.get('account_balance', 10000)  # Default balance
        position_size = self._calculate_position_size(
            account_balance, 
            entry_price, 
            sl_price
        )

        # Store entry data
        self.entry_data = {
            'entry_price': entry_price,
            'stop_loss': sl_price,
            'take_profit': tp_price,
            'position_size': position_size,
            'risk_amount': account_balance * (self.params['risk_percent'] / 100),
            'risk_reward_ratio': self.params['risk_reward_ratio'],
            'fvg_zone': fvg_zone
        }
        
        self.entry_triggered = True
        
        self.logger.info(f"Entry signal: LONG at {entry_price:.4f}")
        self.logger.info(f"  SL: {sl_price:.4f} | TP: {tp_price:.4f}")
        self.logger.info(f"  Position Size: {position_size:.4f}")
        self.logger.info(f"  R:R = 1:{self.params['risk_reward_ratio']}")
        
        return True

    def get_signal(self, market_data: Dict[str, Any]) -> str:
        """
        Get signal from entry filter.
        
        Args:
            market_data: Dictionary containing market data
            
        Returns:
            'BUY' if entry conditions met, 'HOLD' otherwise
        """
        if self.analyze(market_data):
            return 'BUY'  # Entry signal - trigger LONG position
        return 'HOLD'

    def _check_retracement(self, candle: Dict[str, Any], 
                          fvg_zone: Dict[str, Any]) -> bool:
        """
        Check if candle closed inside FVG zone.
        
        Args:
            candle: Current candle data
            fvg_zone: FVG zone boundaries
            
        Returns:
            True if candle closed in FVG, False otherwise
        """
        close = float(candle['close'])
        fvg_low = fvg_zone['low']
        fvg_high = fvg_zone['high']
        
        # Check if close is inside FVG zone
        in_zone = fvg_low <= close <= fvg_high
        
        if in_zone:
            self.logger.debug(f"Price in FVG: {close:.4f} (zone: {fvg_low:.4f}-{fvg_high:.4f})")
        
        return in_zone

    def _calculate_stop_loss(self, fvg_zone: Dict[str, Any]) -> float:
        """
        Calculate stop loss below FVG zone.
        
        Args:
            fvg_zone: FVG zone data
            
        Returns:
            Stop loss price
        """
        sl_offset = self.params['sl_offset_pips'] * self.params['pip_value']
        fvg_low = fvg_zone['low']
        
        # Place SL below FVG low with offset
        sl_price = fvg_low - sl_offset
        
        self.logger.debug(f"SL calculated: {sl_price:.4f} (FVG low: {fvg_low:.4f}, offset: {sl_offset:.4f})")
        return sl_price

    def _calculate_take_profit(self, entry_price: float, sl_price: float) -> float:
        """
        Calculate take profit based on risk/reward ratio.
        
        Args:
            entry_price: Entry price
            sl_price: Stop loss price
            
        Returns:
            Take profit price
        """
        risk_reward = self.params['risk_reward_ratio']
        
        # Calculate risk (distance from entry to SL)
        risk = entry_price - sl_price
        
        # Calculate reward (risk * ratio)
        reward = risk * risk_reward
        
        # TP is entry + reward
        tp_price = entry_price + reward
        
        self.logger.debug(f"TP calculated: {tp_price:.4f} (risk: {risk:.4f}, reward: {reward:.4f})")
        return tp_price

    def _calculate_position_size(self, account_balance: float, 
                                 entry_price: float, 
                                 sl_price: float) -> float:
        """
        Calculate position size based on risk percentage.
        
        Args:
            account_balance: Account balance
            entry_price: Entry price
            sl_price: Stop loss price
            
        Returns:
            Position size in base currency
        """
        risk_percent = self.params['risk_percent']
        
        # Calculate risk amount in quote currency
        risk_amount = account_balance * (risk_percent / 100)
        
        # Calculate risk per unit
        risk_per_unit = entry_price - sl_price
        
        # Calculate position size
        if risk_per_unit > 0:
            position_size = risk_amount / risk_per_unit
        else:
            position_size = 0
        
        self.logger.debug(f"Position size: {position_size:.4f} (risk: {risk_amount:.2f}, per unit: {risk_per_unit:.4f})")
        return position_size

    def get_entry_data(self) -> Optional[Dict[str, Any]]:
        """
        Get entry data with all calculated parameters.
        
        Returns:
            Dictionary with entry data or None
        """
        return self.entry_data

    def is_entry_triggered(self) -> bool:
        """
        Check if entry has been triggered.
        
        Returns:
            True if entry triggered, False otherwise
        """
        return self.entry_triggered

    def get_entry_levels(self) -> Optional[Tuple[float, float, float]]:
        """
        Get entry, SL, and TP levels.
        
        Returns:
            Tuple of (entry, sl, tp) or None
        """
        if self.entry_data:
            return (
                self.entry_data['entry_price'],
                self.entry_data['stop_loss'],
                self.entry_data['take_profit']
            )
        return None

    def reset(self):
        """Reset filter state."""
        self.entry_triggered = False
        self.entry_data = None
