"""
Configuration module for the Binance trading bot.
Reads configuration from environment variables.
"""

import os
import logging
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Configuration class for the trading bot."""

    # Binance API Configuration
    BINANCE_API_KEY: str = os.getenv('BINANCE_API_KEY', '')
    BINANCE_API_SECRET: str = os.getenv('BINANCE_API_SECRET', '')

    # Trading Configuration
    TRADING_PAIR: str = os.getenv('TRADING_PAIR', 'BTCUSDT')
    LEVERAGE: int = int(os.getenv('LEVERAGE', '3'))
    POSITION_SIZE: float = float(os.getenv('POSITION_SIZE', '100'))
    STOP_LOSS_PERCENT: float = float(os.getenv('STOP_LOSS_PERCENT', '2.0'))
    TAKE_PROFIT_PERCENT: float = float(os.getenv('TAKE_PROFIT_PERCENT', '5.0'))

    # Bot Configuration
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    DRY_RUN: bool = os.getenv('DRY_RUN', 'True').lower() in ('true', '1', 'yes')

    # Risk Management
    MAX_POSITION_SIZE: float = float(os.getenv('MAX_POSITION_SIZE', '1000'))
    MIN_POSITION_SIZE: float = float(os.getenv('MIN_POSITION_SIZE', '10'))

    @classmethod
    def validate(cls) -> bool:
        """
        Validate that all required configuration values are set.
        
        Returns:
            bool: True if configuration is valid, False otherwise
        """
        if not cls.BINANCE_API_KEY:
            logging.error("BINANCE_API_KEY is not set")
            return False
        
        if not cls.BINANCE_API_SECRET:
            logging.error("BINANCE_API_SECRET is not set")
            return False
        
        if cls.LEVERAGE < 1 or cls.LEVERAGE > 125:
            logging.error(f"Invalid LEVERAGE value: {cls.LEVERAGE}. Must be between 1 and 125")
            return False
        
        if cls.POSITION_SIZE < cls.MIN_POSITION_SIZE or cls.POSITION_SIZE > cls.MAX_POSITION_SIZE:
            logging.error(
                f"Invalid POSITION_SIZE: {cls.POSITION_SIZE}. "
                f"Must be between {cls.MIN_POSITION_SIZE} and {cls.MAX_POSITION_SIZE}"
            )
            return False
        
        return True

    @classmethod
    def get_log_level(cls) -> int:
        """
        Get the logging level from configuration.
        
        Returns:
            int: Logging level constant
        """
        levels = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL
        }
        return levels.get(cls.LOG_LEVEL.upper(), logging.INFO)

    @classmethod
    def display_config(cls) -> None:
        """Display current configuration (with sensitive data masked)."""
        logging.info("=== Bot Configuration ===")
        logging.info(f"Trading Pair: {cls.TRADING_PAIR}")
        logging.info(f"Leverage: {cls.LEVERAGE}x")
        logging.info(f"Position Size: {cls.POSITION_SIZE}")
        logging.info(f"Stop Loss: {cls.STOP_LOSS_PERCENT}%")
        logging.info(f"Take Profit: {cls.TAKE_PROFIT_PERCENT}%")
        logging.info(f"Dry Run Mode: {cls.DRY_RUN}")
        logging.info(f"Log Level: {cls.LOG_LEVEL}")
        logging.info(f"API Key: {'SET' if cls.BINANCE_API_KEY else 'NOT SET'}")
        logging.info("========================")
