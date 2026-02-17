"""
Base filter class for technical analysis filters.
All custom filters should inherit from this class.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging


class BaseFilter(ABC):
    """
    Abstract base class for trading filters.
    
    Filters are used to determine if trading conditions are met
    based on technical analysis or other criteria.
    """

    def __init__(self, name: str, params: Optional[Dict[str, Any]] = None):
        """
        Initialize the filter.
        
        Args:
            name: Name of the filter
            params: Optional dictionary of filter parameters
        """
        self.name = name
        self.params = params or {}
        self.logger = logging.getLogger(f"{__name__}.{name}")
        self.logger.info(f"Filter '{name}' initialized with params: {self.params}")

    @abstractmethod
    def analyze(self, market_data: Dict[str, Any]) -> bool:
        """
        Analyze market data and return whether conditions are met.
        
        Args:
            market_data: Dictionary containing market data (price, volume, etc.)
            
        Returns:
            True if filter conditions are met, False otherwise
        """
        pass

    @abstractmethod
    def get_signal(self, market_data: Dict[str, Any]) -> str:
        """
        Get trading signal from the filter.
        
        Args:
            market_data: Dictionary containing market data
            
        Returns:
            Trading signal: 'BUY', 'SELL', or 'HOLD'
        """
        pass

    def validate_market_data(self, market_data: Dict[str, Any], required_keys: list) -> bool:
        """
        Validate that market data contains required keys.
        
        Args:
            market_data: Market data dictionary
            required_keys: List of required keys
            
        Returns:
            True if all required keys are present, False otherwise
        """
        for key in required_keys:
            if key not in market_data:
                self.logger.error(f"Missing required key in market data: {key}")
                return False
        return True

    def get_description(self) -> str:
        """
        Get a description of the filter and its parameters.
        
        Returns:
            String description of the filter
        """
        return f"{self.name} filter with parameters: {self.params}"

    def __str__(self) -> str:
        """String representation of the filter."""
        return f"<{self.__class__.__name__}: {self.name}>"

    def __repr__(self) -> str:
        """Detailed string representation of the filter."""
        return f"{self.__class__.__name__}(name='{self.name}', params={self.params})"


class SimpleFilter(BaseFilter):
    """
    Simple example filter implementation.
    
    This is a basic filter that always returns True for demonstration purposes.
    Real filters should implement more sophisticated analysis.
    """

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """Initialize the simple filter."""
        super().__init__("SimpleFilter", params)

    def analyze(self, market_data: Dict[str, Any]) -> bool:
        """
        Simple analysis that checks if price data exists.
        
        Args:
            market_data: Dictionary containing market data
            
        Returns:
            True if price data exists, False otherwise
        """
        if not self.validate_market_data(market_data, ['price']):
            return False
        
        self.logger.debug(f"Analyzing market data: {market_data}")
        return True

    def get_signal(self, market_data: Dict[str, Any]) -> str:
        """
        Get signal from simple filter.
        
        Args:
            market_data: Dictionary containing market data
            
        Returns:
            'HOLD' signal
        """
        if self.analyze(market_data):
            return 'HOLD'
        return 'HOLD'
