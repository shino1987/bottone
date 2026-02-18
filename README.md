# Bottone - Trading Bot

A multi-pair cryptocurrency trading bot with automated trade execution and position monitoring.

## Features

- ✅ **Automated Trade Execution** - Opens trades when entry signals are detected
- ✅ **Position Monitoring** - Continuously checks if Take Profit or Stop Loss levels are hit
- ✅ **Trade Closure** - Automatically closes positions when TP/SL are reached
- ✅ **Trade Tracking** - Logs all trade history with entry/exit times and P&L
- ✅ **DRY RUN Mode** - Test strategies without risking real funds
- ✅ **Multi-Pair Support** - Monitor and trade multiple cryptocurrency pairs simultaneously

## Architecture

### Core Components

1. **trade_executor.py** - Handles opening, closing, and monitoring trades
   - Opens trades (real or simulated)
   - Monitors positions for TP/SL triggers
   - Closes trades and calculates P&L
   - Logs trade history to CSV

2. **main.py** - Main bot orchestration
   - Integrates monitor and executor
   - Processes entry signals
   - Manages continuous monitoring loop

3. **multi_pair_monitor.py** - Multi-pair signal monitoring
   - Monitors multiple trading pairs
   - Generates entry signals
   - Maintains signal queue

4. **binance_api.py** - Binance API wrapper
   - Gets current prices
   - Places orders
   - Handles API communication

5. **config.py** - Configuration settings
   - Trading mode (DRY_RUN/LIVE)
   - API credentials
   - Trading parameters

## Installation

```bash
# Clone the repository
git clone https://github.com/shino1987/bottone.git
cd bottone

# Install dependencies (if any are added in the future)
pip install -r requirements.txt
```

## Configuration

Edit `config.py` to configure the bot:

```python
class Config:
    # Trading mode
    DRY_RUN = True  # Set to False for live trading
    
    # Binance API credentials
    API_KEY = "your_api_key"
    API_SECRET = "your_api_secret"
    
    # Trading parameters
    DEFAULT_POSITION_SIZE = 100  # Default position size in USD
    
    # Monitoring intervals
    SIGNAL_CHECK_INTERVAL = 10  # Seconds between position checks
    MONITOR_UPDATE_INTERVAL = 30  # Seconds between signal updates
```

## Usage

### Running the Bot

```bash
python main.py
```

The bot will:
1. Start monitoring for entry signals
2. Open trades when signals are found
3. Monitor all open positions every 10 seconds
4. Close trades when TP or SL levels are hit
5. Log all trades to `trade_history.csv`

### Running Tests

```bash
python test_bot.py
```

This will run comprehensive tests covering:
- Trade opening and closing
- Take Profit execution
- Stop Loss execution
- Multiple position management
- Trade history logging
- Monitor-executor integration

## Trade Flow

```
1. Monitor detects entry signal
   ↓
2. Executor opens trade
   - Logs entry price, TP, SL
   - Records entry time
   ↓
3. Continuous monitoring (every 10s)
   - Checks current price vs TP/SL
   ↓
4. When TP or SL hit:
   - Closes position
   - Calculates P&L
   - Logs to trade_history.csv
```

## Trade History

All completed trades are logged to `trade_history.csv`:

```csv
symbol,entry_price,exit_price,reason,pnl,entry_time,exit_time
BTCUSDT,50000.00,52000.00,TAKE_PROFIT,200.00,2026-02-18 06:26:46,2026-02-18 06:26:46
BTCUSDT,50000.00,49000.00,STOP_LOSS,-100.00,2026-02-18 06:26:46,2026-02-18 06:26:46
```

## DRY RUN Mode

By default, the bot runs in DRY RUN mode, which:
- Simulates all trades without executing them on Binance
- Provides full logging and P&L calculations
- Perfect for testing strategies
- No risk to real funds

To enable live trading, set `Config.DRY_RUN = False` and provide valid API credentials.

## Logging

The bot creates two log files:
- `trading_bot.log` - Detailed bot operations log
- Console output - Real-time activity display

## Safety Features

- DRY RUN mode by default
- Clear logging of all operations
- Automatic position monitoring
- Stop Loss protection
- Trade history for analysis

## Project Status

**FIXED**: ✅ Trading bot now executes trades and monitors positions correctly

The bot now:
- ✅ Opens trades when entry signals are found
- ✅ Monitors positions continuously
- ✅ Closes trades when TP/SL are hit
- ✅ Logs complete trade history
- ✅ Calculates and displays P&L

## License

MIT License
