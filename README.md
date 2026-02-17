# Bottone - Binance Trading Bot

Un bot di trading automatico per Binance con supporto per ordini a margine incrociato e strategia di trading a 7 step.

## Caratteristiche

- 🔌 **Integrazione Binance API**: Supporto completo per ordini a margine incrociato
- ⚙️ **Configurazione flessibile**: Tutte le impostazioni tramite variabili d'ambiente
- 🔍 **Sistema modulare di filtri**: Architettura estensibile per filtri di analisi tecnica
- 📈 **Strategia a 7 Step**: Implementazione completa della strategia di trading con validazione multi-step
- 🔄 **Multi-Pair Monitoring**: Monitoraggio parallelo di 20 coppie USDC con threading
- 🤖 **State Machine**: Gestione automatica del flusso tra i 7 step con timeout
- 🛡️ **Risk Management**: Gestione automatica di leva, stop loss e take profit con ratio 1:3
- 📊 **Logging completo**: Tracciamento dettagliato di tutte le operazioni
- 🏗️ **Struttura modulare**: Facile da estendere e manutenere

## Strategia di Trading a 7 Step

Il bot implementa una strategia completa in 7 fasi:

1. **Market Structure**: Validazione volume minimo (1M USDT) e struttura di mercato
2. **Downtrend**: Rilevamento di 2-3 lower lows e lower highs consecutivi
3. **Liquidity Sweep**: Identificazione di sweep di liquidità e zona di domanda
4. **CHOCH (Change of Character)**: Rilevamento di rottura della struttura e cambio trend
5. **MMS (Market Structure Shift)**: Conferma del primo higher low dopo CHOCH
6. **Bullish FVG**: Identificazione di Fair Value Gap rialzista (gap a 3 candele)
7. **Entry**: Ingresso LONG con calcolo automatico di SL/TP (ratio 1:3)

## Struttura del Progetto

```
bottone/
├── config.py                    # Configurazione da variabili d'ambiente
├── binance_api.py               # Wrapper API Binance per margine incrociato
├── bot.py                       # Logica principale del bot di trading
├── main.py                      # Entry point dell'applicazione
├── multi_pair_monitor.py        # Monitor multi-coppia con threading
├── filters/
│   ├── __init__.py
│   ├── base_filter.py           # Classe base per i filtri
│   ├── market_structure.py      # Step 1: Validazione struttura mercato
│   ├── downtrend.py             # Step 2: Rilevamento downtrend
│   ├── liquidity_sweep.py       # Step 3: Sweep di liquidità
│   ├── choch.py                 # Step 4: Change of Character
│   ├── mms.py                   # Step 5: Market Structure Shift
│   ├── bullish_fvg.py           # Step 6: Bullish Fair Value Gap
│   ├── entry.py                 # Step 7: Logica di entrata
│   └── state_machine.py         # State machine per gestione flusso
├── requirements.txt             # Dipendenze Python
├── .env.example                 # Template variabili d'ambiente
└── .gitignore                   # File da ignorare in git
```

## Installazione

1. **Clonare il repository**:
```bash
git clone https://github.com/shino1987/bottone.git
cd bottone
```

2. **Installare le dipendenze**:
```bash
pip install -r requirements.txt
```

3. **Configurare le variabili d'ambiente**:
```bash
cp .env.example .env
# Modificare .env con le proprie chiavi API e configurazioni
```

## Configurazione

Creare un file `.env` nella root del progetto con le seguenti variabili:

```env
# Binance API Configuration
BINANCE_API_KEY=your_api_key_here
BINANCE_API_SECRET=your_api_secret_here

# Trading Configuration
TRADING_PAIR=BTCUSDT
LEVERAGE=3
POSITION_SIZE=100
STOP_LOSS_PERCENT=2.0
TAKE_PROFIT_PERCENT=5.0

# Bot Configuration
LOG_LEVEL=INFO
DRY_RUN=True
BOT_MODE=multi-pair  # Options: 'single-pair' or 'multi-pair'

# Risk Management
MAX_POSITION_SIZE=1000
MIN_POSITION_SIZE=10
```

### Parametri di Configurazione

- **BINANCE_API_KEY**: Chiave API Binance (obbligatorio)
- **BINANCE_API_SECRET**: Secret API Binance (obbligatorio)
- **TRADING_PAIR**: Coppia di trading (es. BTCUSDT) - usato solo in modalità single-pair
- **LEVERAGE**: Leva finanziaria (1-125)
- **POSITION_SIZE**: Dimensione della posizione in USDT
- **STOP_LOSS_PERCENT**: Percentuale di stop loss
- **TAKE_PROFIT_PERCENT**: Percentuale di take profit
- **LOG_LEVEL**: Livello di logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- **DRY_RUN**: Modalità test senza eseguire ordini reali (True/False)
- **BOT_MODE**: Modalità operativa - `single-pair` o `multi-pair` (default: multi-pair)

## Utilizzo

### Modalità Multi-Pair (Consigliata)

La modalità multi-pair monitora simultaneamente 20 coppie USDC utilizzando threading:

**Coppie monitorate:**
- BTCUSDC, ETHUSDC, SOLUSDC, BNBUSDC, ADAUSDC
- XRPUSDC, DOGEUSDC, LTCUSDC, MATICUSDC, AVAXUSDC
- UNIUSDC, LINKUSDC, ARBUSDC, OPUSDC, FTMUSDC
- ONEUSDC, APTUSDC, SUIUSDC, PEPEUSDC, GALEUSDC

```bash
# Impostare BOT_MODE=multi-pair nel file .env
python main.py
```

Il bot:
- Monitora tutte le coppie in parallelo
- Applica la strategia a 7 step a ciascuna coppia indipendentemente
- Mostra statistiche in tempo reale ogni 5 minuti
- Genera segnali di entrata quando tutti i 7 step sono completati

### Modalità Single-Pair

Per monitorare una singola coppia con i filtri originali:

```bash
# Impostare BOT_MODE=single-pair nel file .env
python main.py
```

### Modalità Dry Run (Test)

Per testare il bot senza eseguire ordini reali:

```bash
# Assicurarsi che DRY_RUN=True nel file .env
python main.py
```

### Modalità Trading Reale

⚠️ **ATTENZIONE**: Il trading reale comporta rischi finanziari!

```bash
# Impostare DRY_RUN=False nel file .env
python main.py
```

## Strategia a 7 Step - Dettagli

### Step 1: Market Structure (market_structure.py)
- Valida volume minimo (1M USDT)
- Identifica struttura di mercato (ranging/trending_up/trending_down)
- Controlla gap anomali (max 2%)
- Verifica movimento sufficiente dei prezzi (min 0.5%)

### Step 2: Downtrend (downtrend.py)
- Rileva 2-3 lower lows consecutivi
- Rileva 2-3 lower highs consecutivi
- Conferma con pendenza MA negativa (periodo 20)
- Ritorna TRUE quando downtrend confermato

### Step 3: Liquidity Sweep (liquidity_sweep.py)
- Identifica precedente swing low (liquidità buyside)
- Trova break sopra (sweep di liquidità)
- Identifica zona di domanda (accumulo volume)
- Ritorna TRUE quando sweep + domanda trovati

### Step 4: CHOCH - Change of Character (choch.py)
- Monitora struttura di mercato (rottura struttura)
- Identifica rotazione del trend
- Candela close sopra ultimo swing low
- Ritorna TRUE quando CHOCH verificato

### Step 5: MMS - Market Structure Shift (mms.py)
- Identifica primo higher low dopo CHOCH
- Conferma rotazione struttura
- Ritorna TRUE quando MMS formato

### Step 6: Bullish FVG - Fair Value Gap (bullish_fvg.py)
- Identifica FVG rialzista (gap a 3 candele)
- Candela 1 e 3 non si toccano
- Traccia ritracciamento prezzo in FVG
- Ritorna TRUE quando FVG formato

### Step 7: Entry (entry.py)
- Monitora ritracciamento prezzo in FVG
- Candela close dentro FVG
- Calcola SL sotto FVG (5 pips)
- Calcola TP con ratio 1:3 rischio/rendimento
- Ritorna TRUE e triggera entrata LONG

### State Machine (state_machine.py)
- Flusso stati: IDLE → STEP1 → STEP2 → ... → STEP7 → POSITION_OPEN
- Transizioni automatiche tra step
- Timeout per step (240 minuti / 4 ore default)
- Reset stato se condizioni non soddisfatte
- Logging completo delle transizioni

## Risk Management

Il bot implementa automaticamente:
- **Stop Loss**: Posizionato sotto FVG con offset di 5 pips
- **Take Profit**: Calcolato con ratio 1:3 rischio/rendimento
- **Position Size**: Basato su 2% di rischio del balance
- **Timeframe**: 15 minuti (fisso)
- **Analisi Candele**: Ultime 50 candele
- **Timeout Step**: 240 minuti (4 ore) per step

## Filtri di Analisi

Il bot utilizza un sistema modulare di filtri per determinare quando aprire o chiudere posizioni. 

### Creare un Filtro Personalizzato

```python
from filters.base_filter import BaseFilter
from typing import Dict, Any

class MyCustomFilter(BaseFilter):
    def __init__(self, params=None):
        super().__init__("MyCustomFilter", params)
    
    def analyze(self, market_data: Dict[str, Any]) -> bool:
        # Implementare la logica di analisi
        price = market_data['price']
        # ... la tua logica ...
        return True
    
    def get_signal(self, market_data: Dict[str, Any]) -> str:
        if self.analyze(market_data):
            return 'BUY'  # o 'SELL' o 'HOLD'
        return 'HOLD'
```

### Aggiungere un Filtro al Bot

In `main.py`, aggiungere il filtro alla lista:

```python
from my_filters import MyCustomFilter

filters = [
    SimpleFilter(),
    MyCustomFilter(params={'threshold': 0.5})
]
```

## Logging

Il bot genera log in due posizioni:
- **Console**: Output in tempo reale
- **File**: `trading_bot.log` nella directory del progetto

### Log della State Machine

La state machine genera log dettagliati per ogni transizione:
```
INFO:filters.state_machine:State transition: IDLE → STEP1_MARKET_STRUCTURE
INFO:filters.base_filter.MarketStructure:Market structure identified: trending_down
INFO:filters.state_machine:State transition: STEP1_MARKET_STRUCTURE → STEP2_DOWNTREND
```

### Statistiche Multi-Pair

In modalità multi-pair, il bot mostra statistiche ogni 5 minuti:
```
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
...
```

## Sicurezza

⚠️ **IMPORTANTE**:
- Non condividere mai le chiavi API
- Utilizzare sempre la modalità DRY_RUN per testare nuove strategie
- Iniziare con importi piccoli
- Il file `.env` è escluso dal repository tramite `.gitignore`

## Sviluppo

### Test

```bash
# Test di importazione dei moduli base
python -c "import config, binance_api, bot; from filters.base_filter import BaseFilter; print('OK')"

# Test di importazione della strategia a 7 step
python -c "from filters.state_machine import TradingStateMachine; from multi_pair_monitor import MultiPairMonitor; print('7-Step Strategy OK')"
```

### Struttura dei Moduli

- **config.py**: Gestione della configurazione e validazione
- **binance_api.py**: Wrapper per l'API Binance con supporto margine incrociato
- **bot.py**: Logica principale del bot, gestione ordini e risk management
- **multi_pair_monitor.py**: Monitoraggio multi-coppia con threading
- **filters/**: Modulo per filtri di analisi tecnica
  - **state_machine.py**: State machine per gestione flusso strategia
  - **market_structure.py - entry.py**: Filtri per i 7 step
- **main.py**: Entry point e inizializzazione del bot

## Contribuire

Contributi, issues e feature requests sono benvenuti!

## Licenza

Questo progetto è fornito "as is" senza garanzie. Utilizzare a proprio rischio.

## Disclaimer

⚠️ **DISCLAIMER**: Questo bot è fornito solo a scopo educativo. Il trading comporta rischi significativi di perdita finanziaria. Non investire più di quanto sei disposto a perdere. L'autore non è responsabile per eventuali perdite finanziarie.
