"""
State machine for tracking progression through the 7-step trading strategy.

States:
0: No position - Search for buyside liquidity
1: Buyside Liquidity found - Search for downtrend
2: Downtrend confirmed - Search for liquidity sweep + demand zone
3: Liquidity Sweep found - Wait for CHOCH (Change of Character)
4: CHOCH verified - Wait for MMS (Market Structure Shift)
5: MMS created - Wait for Bullish FVG (Fair Value Gap)
6: Bullish FVG formed - Wait for retracement + entry
7: Entry long executed
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime


class TradingStateMachine:
    """
    State machine to track progression through the 7-step trading strategy.
    """
    
    # State definitions
    STATE_NO_POSITION = 0
    STATE_BUYSIDE_LIQUIDITY_FOUND = 1
    STATE_DOWNTREND_CONFIRMED = 2
    STATE_LIQUIDITY_SWEEP_FOUND = 3
    STATE_CHOCH_VERIFIED = 4
    STATE_MMS_CREATED = 5
    STATE_BULLISH_FVG_FORMED = 6
    STATE_ENTRY_EXECUTED = 7
    
    STATE_DESCRIPTIONS = {
        0: "No position - Search for buyside liquidity",
        1: "Buyside Liquidity found - Search for downtrend",
        2: "Downtrend confirmed - Search for liquidity sweep + demand zone",
        3: "Liquidity Sweep found - Wait for CHOCH",
        4: "CHOCH verified - Wait for MMS",
        5: "MMS created - Wait for Bullish FVG",
        6: "Bullish FVG formed - Wait for retracement + entry",
        7: "Entry long executed"
    }
    
    def __init__(self, symbol: str):
        """
        Initialize state machine for a trading pair.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTCUSDC')
        """
        self.symbol = symbol
        self.current_state = self.STATE_NO_POSITION
        self.logger = logging.getLogger(f"{__name__}.{symbol}")
        
        # Historical data for each state
        self.state_data: Dict[int, Dict[str, Any]] = {}
        
        # State transition history
        self.transition_history = []
        
        self.logger.info(f"State machine initialized for {symbol}")
    
    def get_current_state(self) -> int:
        """
        Get the current state.
        
        Returns:
            Current state number
        """
        return self.current_state
    
    def get_state_description(self, state: Optional[int] = None) -> str:
        """
        Get the description of a state.
        
        Args:
            state: State number (defaults to current state)
            
        Returns:
            State description string
        """
        if state is None:
            state = self.current_state
        return self.STATE_DESCRIPTIONS.get(state, f"Unknown state {state}")
    
    def transition_to(self, new_state: int, data: Optional[Dict[str, Any]] = None) -> bool:
        """
        Transition to a new state.
        
        Args:
            new_state: Target state number
            data: Optional data associated with the transition
            
        Returns:
            True if transition was successful, False otherwise
        """
        if new_state < 0 or new_state > self.STATE_ENTRY_EXECUTED:
            self.logger.error(f"Invalid state: {new_state}")
            return False
        
        # Log the transition
        old_state = self.current_state
        old_desc = self.get_state_description(old_state)
        new_desc = self.get_state_description(new_state)
        
        self.logger.info(f"State transition: [{old_state}] {old_desc} -> [{new_state}] {new_desc}")
        
        # Record transition in history
        transition_record = {
            'timestamp': datetime.now().isoformat(),
            'from_state': old_state,
            'to_state': new_state,
            'from_description': old_desc,
            'to_description': new_desc,
            'data': data or {}
        }
        self.transition_history.append(transition_record)
        
        # Update current state
        self.current_state = new_state
        
        # Store state data
        if data:
            self.state_data[new_state] = {
                'timestamp': datetime.now().isoformat(),
                'data': data
            }
        
        return True
    
    def reset(self) -> None:
        """
        Reset the state machine to initial state.
        """
        self.logger.info(f"Resetting state machine for {self.symbol}")
        self.current_state = self.STATE_NO_POSITION
        self.state_data = {}
        # Keep transition history for analysis
    
    def get_state_data(self, state: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Get data stored for a specific state.
        
        Args:
            state: State number (defaults to current state)
            
        Returns:
            State data dictionary or None
        """
        if state is None:
            state = self.current_state
        return self.state_data.get(state)
    
    def get_transition_history(self, limit: Optional[int] = None) -> list:
        """
        Get state transition history.
        
        Args:
            limit: Maximum number of recent transitions to return (None for all)
            
        Returns:
            List of transition records
        """
        if limit:
            return self.transition_history[-limit:]
        return self.transition_history
    
    def can_transition_to(self, target_state: int) -> bool:
        """
        Check if transition to target state is valid from current state.
        
        Args:
            target_state: Target state number
            
        Returns:
            True if transition is valid, False otherwise
        """
        # Basic validation - state should progress or reset
        if target_state == self.STATE_NO_POSITION:
            # Can always reset to initial state
            return True
        
        # Generally, we progress sequentially or stay in same state
        if target_state == self.current_state or target_state == self.current_state + 1:
            return True
        
        # Allow jumping back to certain states (e.g., on invalidation)
        if target_state < self.current_state:
            self.logger.warning(f"Backwards transition from {self.current_state} to {target_state}")
            return True
        
        # Don't allow skipping states
        self.logger.warning(f"Invalid state jump from {self.current_state} to {target_state}")
        return False
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get comprehensive status of the state machine.
        
        Returns:
            Dictionary with status information
        """
        return {
            'symbol': self.symbol,
            'current_state': self.current_state,
            'state_description': self.get_state_description(),
            'state_data': self.get_state_data(),
            'transition_count': len(self.transition_history),
            'last_transition': self.transition_history[-1] if self.transition_history else None
        }
