# Bottone - Binance Trading Bot

Un bot di trading automatico per Binance con supporto per ordini a margine incrociato.

## Caratteristiche

- 🔌 **Integrazione Binance API**: Supporto completo per ordini a margine incrociato
- ⚙️ **Configurazione flessibile**: Tutte le impostazioni tramite variabili d'ambiente
- 🔍 **Sistema modulare di filtri**: Architettura estensibile per filtri di analisi tecnica
- 🛡️ **Risk Management**: Gestione automatica di leva, stop loss e take profit
- 📊 **Logging completo**: Tracciamento dettagliato di tutte le operazioni
- 🏗️ **Struttura modulare**: Facile da estendere e manutenere
- 🎯 **Buyside Liquidity Filter**: Identifica zone di liquidità su swing low
- 🔄 **State Machine**: Traccia la progressione attraverso 7 step strategici
- 📈 **Analisi OHLCV**: Dati candlestick 15 minuti da Binance
- 🌐 **Multi-pair Support**: Monitoraggio simultaneo di 20 coppie USDC

## Struttura del Progetto

```
bottone/
├── config.py                      # Configurazione da variabili d'ambiente
├── binance_api.py                 # Wrapper API Binance per margine incrociato
├── filters/
│   ├── __init__.py
│   ├── base_filter.py             # Classe base per i filtri di analisi
│   ├── buyside_liquidity.py       # Filtro per identificare liquidity ai swing low
│   └── state_machine.py           # State machine per i 7 step della strategia
├── bot.py                         # Logica principale del bot di trading
├── main.py                        # Entry point dell'applicazione
├── requirements.txt               # Dipendenze Python
├── .env.example                   # Template variabili d'ambiente
├── .gitignore                     # File da ignorare in git
└── STEP1_IMPLEMENTATION.md        # Documentazione implementazione Step 1
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

# Risk Management
MAX_POSITION_SIZE=1000
MIN_POSITION_SIZE=10
```

### Parametri di Configurazione

- **BINANCE_API_KEY**: Chiave API Binance (obbligatorio)
- **BINANCE_API_SECRET**: Secret API Binance (obbligatorio)
- **TRADING_PAIR**: Coppia di trading (es. BTCUSDT)
- **LEVERAGE**: Leva finanziaria (1-125)
- **POSITION_SIZE**: Dimensione della posizione in USDT
- **STOP_LOSS_PERCENT**: Percentuale di stop loss
- **TAKE_PROFIT_PERCENT**: Percentuale di take profit
- **LOG_LEVEL**: Livello di logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- **DRY_RUN**: Modalità test senza eseguire ordini reali (True/False)

## Utilizzo

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

## Risk Management

Il bot implementa automaticamente:
- **Stop Loss**: Chiusura automatica della posizione al raggiungimento della perdita massima
- **Take Profit**: Chiusura automatica della posizione al raggiungimento del profitto target
- **Controllo della posizione**: Validazione della dimensione della posizione
- **Gestione della leva**: Configurazione della leva finanziaria

## Sicurezza

⚠️ **IMPORTANTE**:
- Non condividere mai le chiavi API
- Utilizzare sempre la modalità DRY_RUN per testare nuove strategie
- Iniziare con importi piccoli
- Il file `.env` è escluso dal repository tramite `.gitignore`

## Sviluppo

### Test

```bash
# Test di importazione dei moduli
python -c "import config, binance_api, bot; from filters.base_filter import BaseFilter; print('OK')"
```

### Struttura dei Moduli

- **config.py**: Gestione della configurazione e validazione
- **binance_api.py**: Wrapper per l'API Binance con supporto margine incrociato
- **bot.py**: Logica principale del bot, gestione ordini e risk management
- **filters/**: Modulo per filtri di analisi tecnica
  - **base_filter.py**: Classe base per tutti i filtri
  - **buyside_liquidity.py**: Filtro per identificare liquidity ai swing low
  - **state_machine.py**: State machine per tracciare i 7 step della strategia
- **main.py**: Entry point e inizializzazione del bot

## Step 1: Buyside Liquidity Filter

Il bot ora implementa il primo step della strategia di trading:

### Funzionalità

1. **Identificazione Swing Low**: Analizza gli ultimi 50 candlestick a 15 minuti per identificare swing low (minimi locali)

2. **Calcolo Zone di Liquidità**: Identifica zone di liquidità basate su volume e supporto

3. **State Machine a 7 Step**: 
   - State 0: Nessuna posizione (cerca buyside liquidity)
   - State 1: Buyside Liquidity trovata (cerca downtrend)
   - State 2: Downtrend confermato (cerca liquidity sweep + demand zone)
   - State 3: Liquidity Sweep trovato (attendi CHOCH)
   - State 4: CHOCH verificato (attendi MMS)
   - State 5: MMS creato (attendi Bullish FVG)
   - State 6: Bullish FVG formata (attendi ritraccia + entry)
   - State 7: Entry long eseguito

4. **Multi-pair Support**: Monitora simultaneamente 20 coppie USDC:
   - BTCUSDC, ETHUSDC, BNBUSDC, ADAUSDC, DOGEUSDC
   - XRPUSDC, DOTUSDC, UNIUSDC, LTCUSDC, LINKUSDC
   - SOLUSDC, MATICUSDC, AVAXUSDC, ATOMUSDC, ETCUSDC
   - ALGOUSDC, XLMUSDC, VETUSDC, ICPUSDC, FILUSDC

### Documentazione Dettagliata

Per maggiori dettagli sull'implementazione di Step 1, vedere [STEP1_IMPLEMENTATION.md](STEP1_IMPLEMENTATION.md).

## Contribuire

Contributi, issues e feature requests sono benvenuti!

## Licenza

Questo progetto è fornito "as is" senza garanzie. Utilizzare a proprio rischio.

## Disclaimer

⚠️ **DISCLAIMER**: Questo bot è fornito solo a scopo educativo. Il trading comporta rischi significativi di perdita finanziaria. Non investire più di quanto sei disposto a perdere. L'autore non è responsabile per eventuali perdite finanziarie.
