"""
State Machine for 7-Step Trading Strategy
Manages the flow through all filter steps with timeouts and transitions.
"""

from enum import Enum
from typing import Dict, Any, Optional
import logging
import time
from datetime import datetime, timedelta

from filters.buyside_liquidity import BuysideLiquidityFilter
from filters.downtrend import DowntrendFilter
from filters.liquidity_sweep import LiquiditySweepFilter
from filters.choch import CHOCHFilter
from filters.mms import MMSFilter
from filters.bullish_fvg import BullishFVGFilter
from filters.entry import EntryFilter


class TradingState(Enum):
    """Trading state enumeration."""
    IDLE = "IDLE"
    STEP1_BUYSIDE_LIQUIDITY = "STEP1_BUYSIDE_LIQUIDITY"
    STEP2_DOWNTREND = "STEP2_DOWNTREND"
    STEP3_LIQUIDITY_SWEEP = "STEP3_LIQUIDITY_SWEEP"
    STEP4_CHOCH = "STEP4_CHOCH"
    STEP5_MMS = "STEP5_MMS"
    STEP6_BULLISH_FVG = "STEP6_BULLISH_FVG"
    STEP7_ENTRY = "STEP7_ENTRY"
    POSITION_OPEN = "POSITION_OPEN"
    FAILED = "FAILED"


class TradingStateMachine:
    """
    State machine for 7-step trading strategy.
    
    State flow: IDLE → STEP1 → STEP2 → ... → STEP7 → POSITION_OPEN
    - Automatic transitions between steps
    - Timeout per step (240 minutes / 4 hours default)
    - Reset state if conditions not met
    - Complete logging of transitions
    """

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """
        Initialize the state machine.
        
        Args:
            params: Optional parameters for configuration
        """
        self.logger = logging.getLogger(__name__)
        
        # Parameters
        default_params = {
            'step_timeout_minutes': 240,  # 4 hours timeout per step
            'candles_per_analysis': 50,  # Number of candles to analyze
        }
        self.params = {**default_params, **(params or {})}
        
        # State management
        self.current_state = TradingState.IDLE
        self.state_entry_time = datetime.now()
        self.state_data = {}
        
        # Initialize all filters
        self.filters = {
            'buyside_liquidity': BuysideLiquidityFilter(),
            'downtrend': DowntrendFilter(),
            'liquidity_sweep': LiquiditySweepFilter(),
            'choch': CHOCHFilter(),
            'mms': MMSFilter(),
            'bullish_fvg': BullishFVGFilter(),
            'entry': EntryFilter(),
        }
        
        self.logger.info("Trading State Machine initialized")
        self.logger.info(f"Step timeout: {self.params['step_timeout_minutes']} minutes")

    def process(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process market data and advance through states.
        
        Args:
            market_data: Market data dictionary with candles
            
        Returns:
            Dictionary with current state and any signals
        """
        # Check for timeout
        if self._check_timeout():
            self.logger.warning(f"Timeout in state {self.current_state.value}")
            self.reset()
            return self._get_status()
        
        # Process current state
        if self.current_state == TradingState.IDLE:
            self._process_idle()
        elif self.current_state == TradingState.STEP1_BUYSIDE_LIQUIDITY:
            self._process_step1(market_data)
        elif self.current_state == TradingState.STEP2_DOWNTREND:
            self._process_step2(market_data)
        elif self.current_state == TradingState.STEP3_LIQUIDITY_SWEEP:
            self._process_step3(market_data)
        elif self.current_state == TradingState.STEP4_CHOCH:
            self._process_step4(market_data)
        elif self.current_state == TradingState.STEP5_MMS:
            self._process_step5(market_data)
        elif self.current_state == TradingState.STEP6_BULLISH_FVG:
            self._process_step6(market_data)
        elif self.current_state == TradingState.STEP7_ENTRY:
            self._process_step7(market_data)
        
        return self._get_status()

    def _check_timeout(self) -> bool:
        """Check if current state has timed out."""
        if self.current_state in [TradingState.IDLE, TradingState.POSITION_OPEN]:
            return False
        
        timeout_minutes = self.params['step_timeout_minutes']
        elapsed = datetime.now() - self.state_entry_time
        
        return elapsed > timedelta(minutes=timeout_minutes)

    def _transition_to(self, new_state: TradingState):
        """Transition to a new state."""
        old_state = self.current_state
        self.current_state = new_state
        self.state_entry_time = datetime.now()
        
        self.logger.info(f"State transition: {old_state.value} → {new_state.value}")

    def _process_idle(self):
        """Process IDLE state."""
        # Automatically transition to STEP1
        self._transition_to(TradingState.STEP1_BUYSIDE_LIQUIDITY)

    def _process_step1(self, market_data: Dict[str, Any]):
        """Process Step 1: Buyside Liquidity Detection."""
        filter_obj = self.filters['buyside_liquidity']
        
        if filter_obj.analyze(market_data):
            # Buyside liquidity detected, proceed to next step
            buyside_data = filter_obj.get_buyside_liquidity_data()
            if buyside_data:
                self.state_data['buyside_liquidity_price'] = buyside_data['price']
                self.state_data['buyside_liquidity_volume'] = buyside_data['volume']
                self.state_data['buyside_liquidity_index'] = buyside_data['index']
                self._transition_to(TradingState.STEP2_DOWNTREND)
        else:
            # Stay in current step, wait for buyside liquidity
            pass

    def _process_step2(self, market_data: Dict[str, Any]):
        """Process Step 2: Downtrend."""
        filter_obj = self.filters['downtrend']
        
        if filter_obj.analyze(market_data):
            # Downtrend confirmed, proceed to next step
            self.state_data['last_swing_low'] = filter_obj.get_last_swing_low(market_data)
            self._transition_to(TradingState.STEP3_LIQUIDITY_SWEEP)
        else:
            # Stay in current step
            pass

    def _process_step3(self, market_data: Dict[str, Any]):
        """Process Step 3: Liquidity Sweep."""
        filter_obj = self.filters['liquidity_sweep']
        
        if filter_obj.analyze(market_data):
            # Liquidity sweep detected, proceed to next step
            self.state_data['sweep_data'] = filter_obj.get_sweep_data()
            self.state_data['demand_zone'] = filter_obj.get_demand_zone()
            self._transition_to(TradingState.STEP4_CHOCH)
        else:
            # Stay in current step
            pass

    def _process_step4(self, market_data: Dict[str, Any]):
        """Process Step 4: CHOCH."""
        filter_obj = self.filters['choch']
        
        # Pass last swing low to filter
        if 'last_swing_low' in self.state_data:
            market_data['last_swing_low'] = self.state_data['last_swing_low']
        
        if filter_obj.analyze(market_data):
            # CHOCH detected, proceed to next step
            self.state_data['choch_price'] = filter_obj.get_choch_price()
            self._transition_to(TradingState.STEP5_MMS)
        else:
            # Stay in current step
            pass

    def _process_step5(self, market_data: Dict[str, Any]):
        """Process Step 5: MMS."""
        filter_obj = self.filters['mms']
        
        # Pass CHOCH price to filter
        if 'choch_price' in self.state_data:
            market_data['choch_price'] = self.state_data['choch_price']
        
        if filter_obj.analyze(market_data):
            # MMS detected, proceed to next step
            self.state_data['mms_price'] = filter_obj.get_mms_price()
            self._transition_to(TradingState.STEP6_BULLISH_FVG)
        else:
            # Stay in current step
            pass

    def _process_step6(self, market_data: Dict[str, Any]):
        """Process Step 6: Bullish FVG."""
        filter_obj = self.filters['bullish_fvg']
        
        if filter_obj.analyze(market_data):
            # FVG detected, proceed to next step
            self.state_data['fvg_zone'] = filter_obj.get_fvg_zone()
            self._transition_to(TradingState.STEP7_ENTRY)
        else:
            # Stay in current step
            pass

    def _process_step7(self, market_data: Dict[str, Any]):
        """Process Step 7: Entry."""
        filter_obj = self.filters['entry']
        
        # Pass FVG zone to filter
        if 'fvg_zone' in self.state_data:
            market_data['fvg_zone'] = self.state_data['fvg_zone']
        
        if filter_obj.analyze(market_data):
            # Entry triggered, move to position open
            self.state_data['entry_data'] = filter_obj.get_entry_data()
            self._transition_to(TradingState.POSITION_OPEN)
        else:
            # Stay in current step
            pass

    def get_entry_signal(self) -> Optional[Dict[str, Any]]:
        """
        Get entry signal if available.
        
        Returns:
            Entry data dictionary or None
        """
        if self.current_state == TradingState.POSITION_OPEN:
            return self.state_data.get('entry_data')
        return None

    def is_position_open(self) -> bool:
        """Check if a position is open."""
        return self.current_state == TradingState.POSITION_OPEN

    def reset(self):
        """Reset state machine to IDLE."""
        self.logger.info("Resetting state machine to IDLE")
        self.current_state = TradingState.IDLE
        self.state_entry_time = datetime.now()
        self.state_data = {}
        
        # Reset all filters
        for filter_obj in self.filters.values():
            if hasattr(filter_obj, 'reset'):
                filter_obj.reset()

    def position_closed(self):
        """Notify state machine that position was closed."""
        self.logger.info("Position closed, resetting state machine")
        self.reset()

    def _get_status(self) -> Dict[str, Any]:
        """Get current status."""
        elapsed = datetime.now() - self.state_entry_time
        
        return {
            'state': self.current_state.value,
            'state_data': self.state_data,
            'time_in_state': str(elapsed).split('.')[0],  # Remove microseconds
            'entry_signal': self.get_entry_signal(),
        }

    def get_current_state(self) -> TradingState:
        """Get current state."""
        return self.current_state

    def get_state_data(self) -> Dict[str, Any]:
        """Get state data."""
        return self.state_data
