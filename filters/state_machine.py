"""
State Machine for trading strategy.
Manages transitions through all 7 steps.
"""

import logging
import time
from typing import Dict, Any, Optional
from enum import Enum

from filters.downtrend import DowntrendFilter
from filters.liquidity_sweep import LiquiditySweepFilter
from filters.choch import CHOCHFilter
from filters.mms import MMSFilter
from filters.bullish_fvg import BullishFVGFilter
from filters.entry import EntryFilter


class TradingState(Enum):
    """Trading strategy states."""
    IDLE = "IDLE"
    DOWNTREND = "DOWNTREND"
    LIQUIDITY_SWEEP = "LIQUIDITY_SWEEP"
    CHOCH = "CHOCH"
    MMS = "MMS"
    BULLISH_FVG = "BULLISH_FVG"
    ENTRY = "ENTRY"
    POSITION_OPEN = "POSITION_OPEN"


class StateMachine:
    """
    State machine for 7-step trading strategy.
    
    Manages automatic transitions between steps with timeouts and logging.
    """
    
    def __init__(self, symbol: str, timeout_minutes: int = 240):
        """
        Initialize state machine.
        
        Args:
            symbol: Trading pair symbol
            timeout_minutes: Timeout for each step in minutes (default: 240 = 4 hours)
        """
        self.symbol = symbol
        self.timeout_minutes = timeout_minutes
        self.logger = logging.getLogger(f"{__name__}.{symbol}")
        
        # Current state
        self.state = TradingState.IDLE
        self.state_entry_time = time.time()
        
        # Initialize filters
        self.downtrend_filter = DowntrendFilter()
        self.liquidity_sweep_filter = LiquiditySweepFilter()
        self.choch_filter = CHOCHFilter()
        self.mms_filter = MMSFilter()
        self.bullish_fvg_filter = BullishFVGFilter()
        self.entry_filter = EntryFilter()
        
        # State data
        self.state_data = {
            'choch_level': None,
            'fvg_zone': None,
            'demand_zone': None,
            'entry_details': None
        }
        
        self.logger.info(f"State machine initialized for {symbol}")
    
    def _check_timeout(self) -> bool:
        """
        Check if current state has timed out.
        
        Returns:
            True if timed out, False otherwise
        """
        elapsed_minutes = (time.time() - self.state_entry_time) / 60
        return elapsed_minutes > self.timeout_minutes
    
    def _transition_to(self, new_state: TradingState):
        """
        Transition to a new state.
        
        Args:
            new_state: New state to transition to
        """
        old_state = self.state
        self.state = new_state
        self.state_entry_time = time.time()
        
        self.logger.info(f"State transition: {old_state.value} -> {new_state.value}")
    
    def _reset_state(self):
        """Reset state machine to IDLE."""
        self.logger.warning(f"Resetting state machine from {self.state.value}")
        self.state_data = {
            'choch_level': None,
            'fvg_zone': None,
            'demand_zone': None,
            'entry_details': None
        }
        self._transition_to(TradingState.IDLE)
    
    def update(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Update state machine with new market data.
        
        Args:
            market_data: Dictionary with klines and price data
            
        Returns:
            Entry details if entry triggered, None otherwise
        """
        # Check for timeout
        if self._check_timeout() and self.state != TradingState.IDLE:
            self.logger.warning(
                f"State {self.state.value} timed out after {self.timeout_minutes} minutes"
            )
            self._reset_state()
            return None
        
        # Process based on current state
        if self.state == TradingState.IDLE:
            return self._process_idle(market_data)
        elif self.state == TradingState.DOWNTREND:
            return self._process_downtrend(market_data)
        elif self.state == TradingState.LIQUIDITY_SWEEP:
            return self._process_liquidity_sweep(market_data)
        elif self.state == TradingState.CHOCH:
            return self._process_choch(market_data)
        elif self.state == TradingState.MMS:
            return self._process_mms(market_data)
        elif self.state == TradingState.BULLISH_FVG:
            return self._process_bullish_fvg(market_data)
        elif self.state == TradingState.ENTRY:
            return self._process_entry(market_data)
        
        return None
    
    def _process_idle(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process IDLE state - start looking for downtrend."""
        self.logger.debug("Starting analysis from IDLE state")
        self._transition_to(TradingState.DOWNTREND)
        return None
    
    def _process_downtrend(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process DOWNTREND state - Step 2."""
        if self.downtrend_filter.analyze(market_data):
            self.logger.info("Downtrend confirmed, moving to liquidity sweep detection")
            self._transition_to(TradingState.LIQUIDITY_SWEEP)
        else:
            self.logger.debug("Downtrend not confirmed yet")
        
        return None
    
    def _process_liquidity_sweep(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process LIQUIDITY_SWEEP state - Step 3."""
        if self.liquidity_sweep_filter.analyze(market_data):
            self.state_data['demand_zone'] = self.liquidity_sweep_filter.get_demand_zone()
            self.logger.info("Liquidity sweep + demand zone found, waiting for CHOCH")
            self._transition_to(TradingState.CHOCH)
        else:
            self.logger.debug("Liquidity sweep not detected yet")
        
        return None
    
    def _process_choch(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process CHOCH state - Step 4."""
        if self.choch_filter.analyze(market_data):
            self.state_data['choch_level'] = self.choch_filter.get_choch_level()
            self.logger.info(f"CHOCH verified at {self.state_data['choch_level']:.2f}, waiting for MMS")
            self._transition_to(TradingState.MMS)
        else:
            self.logger.debug("CHOCH not verified yet")
        
        return None
    
    def _process_mms(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process MMS state - Step 5."""
        # Pass CHOCH level to market_data for MMS filter
        market_data['choch_level'] = self.state_data['choch_level']
        
        if self.mms_filter.analyze(market_data):
            self.logger.info("MMS confirmed, looking for Bullish FVG")
            self._transition_to(TradingState.BULLISH_FVG)
        else:
            self.logger.debug("MMS not formed yet")
        
        return None
    
    def _process_bullish_fvg(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process BULLISH_FVG state - Step 6."""
        if self.bullish_fvg_filter.analyze(market_data):
            self.state_data['fvg_zone'] = self.bullish_fvg_filter.get_fvg_zone()
            self.logger.info(
                f"Bullish FVG formed at "
                f"[{self.state_data['fvg_zone']['low']:.2f} - {self.state_data['fvg_zone']['high']:.2f}], "
                f"waiting for entry"
            )
            self._transition_to(TradingState.ENTRY)
        else:
            self.logger.debug("Bullish FVG not formed yet")
        
        return None
    
    def _process_entry(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process ENTRY state - Step 7."""
        # Pass FVG zone to market_data for Entry filter
        market_data['fvg_zone'] = self.state_data['fvg_zone']
        
        if self.entry_filter.analyze(market_data):
            entry_details = self.entry_filter.get_entry_details()
            self.state_data['entry_details'] = entry_details
            
            self.logger.info(
                f"ENTRY TRIGGERED! "
                f"Entry: {entry_details['entry']:.2f}, "
                f"SL: {entry_details['stop_loss']:.2f}, "
                f"TP: {entry_details['take_profit']:.2f}"
            )
            
            self._transition_to(TradingState.POSITION_OPEN)
            return entry_details
        else:
            self.logger.debug("Waiting for price to retrace into FVG")
        
        return None
    
    def get_state(self) -> TradingState:
        """Get current state."""
        return self.state
    
    def get_state_data(self) -> Dict[str, Any]:
        """Get current state data."""
        return self.state_data.copy()
    
    def reset_after_trade(self):
        """Reset state machine after a trade is completed."""
        self.logger.info("Trade completed, resetting state machine")
        self._reset_state()
