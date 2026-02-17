# Usage Examples for 7-Step Trading Strategy

## Multi-Pair Mode (Recommended)

Monitor 20 USDC pairs simultaneously with the complete 7-step strategy:

### 1. Configure environment

```bash
# .env file
BINANCE_API_KEY=your_api_key_here
BINANCE_API_SECRET=your_api_secret_here
BOT_MODE=multi-pair
DRY_RUN=True
LOG_LEVEL=INFO
```

### 2. Run the bot

```bash
python main.py
```

### 3. Expected Output

```
================================================================================
MULTI-PAIR MONITOR STATISTICS
================================================================================
Started at: 2024-01-01T12:00:00
Active pairs: 20
Total signals found: 3
Entry queue size: 1

Per-Pair Status:
--------------------------------------------------------------------------------
BTCUSDC      | State: STEP3_LIQUIDITY_SWEEP | Signals: 1   | Errors: 0
ETHUSDC      | State: STEP2_DOWNTREND       | Signals: 0   | Errors: 0
SOLUSDC      | State: STEP1_MARKET_STRUCTURE| Signals: 0   | Errors: 0
...

================================================================================
ENTRY SIGNAL FOUND!
Symbol: BTCUSDC
Timestamp: 2024-01-01T12:05:00
Entry Data: {
  'entry_price': 43250.50,
  'stop_loss': 43100.00,
  'take_profit': 43700.50,
  'position_size': 0.0462,
  'risk_reward_ratio': 3.0
}
================================================================================
```

## Single-Pair Mode

Use the original bot logic with custom filters:

### 1. Configure environment

```bash
# .env file
BINANCE_API_KEY=your_api_key_here
BINANCE_API_SECRET=your_api_secret_here
BOT_MODE=single-pair
TRADING_PAIR=BTCUSDT
DRY_RUN=True
```

### 2. Run the bot

```bash
python main.py
```

## Using State Machine Directly

```python
from filters.state_machine import TradingStateMachine

# Initialize state machine
state_machine = TradingStateMachine()

# Prepare market data
market_data = {
    'symbol': 'BTCUSDC',
    'candles': candles,  # List of 50 OHLCV candles
    'account_balance': 10000,
}

# Process through state machine
status = state_machine.process(market_data)

# Check current state
print(f"Current state: {status['state']}")
print(f"Time in state: {status['time_in_state']}")

# Check for entry signal
if status['entry_signal']:
    entry = status['entry_signal']
    print(f"Entry: {entry['entry_price']}")
    print(f"SL: {entry['stop_loss']}")
    print(f"TP: {entry['take_profit']}")
```

## Using Individual Filters

```python
from filters.market_structure import MarketStructureFilter
from filters.downtrend import DowntrendFilter

# Initialize filters
ms_filter = MarketStructureFilter()
dt_filter = DowntrendFilter()

# Prepare market data
market_data = {
    'candles': candles,  # List of OHLCV candles
}

# Test market structure
if ms_filter.analyze(market_data):
    structure = ms_filter.get_market_structure(market_data)
    print(f"Market structure: {structure}")

# Test downtrend
if dt_filter.analyze(market_data):
    swing_low = dt_filter.get_last_swing_low(market_data)
    print(f"Downtrend confirmed, last swing low: {swing_low}")
```

## Risk Management

The entry filter automatically calculates:

- **Position Size**: Based on 2% risk per trade
- **Stop Loss**: 5 pips below FVG zone
- **Take Profit**: 1:3 risk/reward ratio

Example:
- Entry: 43,250.50
- SL: 43,100.00 (150.50 risk)
- TP: 43,700.50 (450.00 reward = 3x risk)

## Monitoring & Statistics

In multi-pair mode, statistics are printed every 5 minutes showing:
- Current state of each pair
- Number of signals found per pair
- Error count per pair
- Global statistics (total signals, queue size)
