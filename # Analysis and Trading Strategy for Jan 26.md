# Analysis and Trading Strategy Development

## Report Summary

The attached research identifies the 10 most common put and call options traded during significant geopolitical events, with specific parameters for strike selection, expiration timeframes, and position sizing. The report is dated January 2026 and reflects current market conditions including Venezuela intervention, Iran tensions, and Greenland disputes.

---

## Trading Strategy: Geopolitical Event Options Framework

### Core Strategy Parameters

| Parameter | Value | Source Reference |
|-----------|-------|------------------|
| Risk per trade | 2-3% of portfolio capital | Report risk management section |
| Total options exposure | 15-20% max | Report position sizing principles |
| Hedging allocation | 5-10% of protected capital | Report defensive hedging characteristics |
| Speculative allocation | 1-3% per position | Report opportunistic speculation characteristics |
| Cash reserve | 15-20% | Report capital efficiency section |
| Stop-loss trigger | 50% loss | Report stop-loss parameters |
| Profit-taking | 50% off at 100% gain | Report profit-taking discipline |
| Position close threshold | 7 days to expiration | Report time-based management |

### VIX-Based Regime Detection

| VIX Level | Market Regime | Action |
|-----------|---------------|--------|
| Below 15 | Complacency | Increase hedging, buy protection |
| 15-20 | Normal | Maintain baseline positioning |
| 20-30 | Elevated | Selective hedging, volatility harvesting |
| Above 30 | Peak Fear | Reduce hedges, sell volatility |

### Put Options Universe (Defensive)

| Symbol | Type | Strike Selection | DTE Range | Rationale |
|--------|------|------------------|-----------|-----------|
| SPY | Index ETF | 5-10% OTM | 30-60 | Portfolio insurance, broad market |
| QQQ | Index ETF | ATM to 10% OTM | 30-45 | Tech concentration hedge |
| IWM | Index ETF | 5-10% OTM | 30-60 | Small-cap vulnerability |
| XLF | Sector ETF | 10-15% OTM | 60-90 | Financial sector crisis protection |
| EEM | Region ETF | 5-10% OTM | 30-90 | Emerging market risk hedge |
| TLT | Bond ETF | 5-10% OTM | 60-120 | Yield spike protection |
| NVDA | Single Stock | ATM to 10% OTM | 30-60 | AI/semiconductor supply chain risk |
| AAPL | Single Stock | 5-10% OTM | 60-90 | Tariff and supply chain hedge |
| TSLA | Single Stock | 10-20% OTM | 30-60 | High beta volatility hedge |

### Call Options Universe (Opportunistic)

| Symbol | Type | Strike Selection | DTE Range | Rationale |
|--------|------|------------------|-----------|-----------|
| GLD | Commodity ETF | ATM to 5% ITM | 60-180 | Safe-haven gold exposure |
| VIX | Volatility | 25-30 strike | 30-60 | Volatility spike asymmetric play |
| LMT | Defense | ATM to 10% OTM | 60-180 | Defense spending acceleration |
| RTX | Defense | ATM to 10% OTM | 60-180 | Defense spending acceleration |
| TDY | Defense | ATM to 10% OTM | 60-180 | Defense quality exposure |
| AIR | Defense | ATM to 10% OTM | 60-180 | Defense momentum play |
| USO | Commodity ETF | 10-15% OTM | 60-120 | Supply disruption asymmetry |
| TLT | Bond ETF | ATM to 5% OTM | 60-120 | Flight-to-quality scenario |
| XLE | Sector ETF | 5-10% OTM | 60-180 | Energy security premium |
| IWM | Index ETF | 5-10% OTM | 60-120 | Risk-on rotation recovery |
| EEM | Region ETF | ATM to 10% OTM | 90-180 | Contrarian EM recovery |

### Entry Signals

**Protective Put Entry Conditions:**
- VIX below 15 (complacency regime)
- Portfolio beta exceeds 1.0
- Geopolitical headline escalation detected
- Technical support breakdown imminent

**Opportunistic Call Entry Conditions:**
- VIX spike above 25 with subsequent decline
- Safe-haven assets (GLD) breaking out
- Defense sector earnings estimate revisions positive
- Geopolitical sell-off creating dislocation in quality names

### Exit Rules

| Condition | Action |
|-----------|--------|
| 100% gain achieved | Close 50% of position |
| 50% loss incurred | Mandatory full exit |
| 7 DTE reached | Close entire position |
| 30-45 DTE on profitable position | Roll to next cycle |
| VIX spikes 50%+ above entry | Exit VIX calls (take profits in fear) |
| Protective put premium declines 50%+ | Close to reduce insurance costs |

### Position Sizing Formula

```
Position Size = (Portfolio Value × Risk Percentage) / (Option Premium × 100)

Where:
- Risk Percentage = 2-3% for individual trades
- Maximum contracts = Portfolio Value × 0.20 / (Option Premium × 100)
```

### Crisis Phase Allocation Adjustments

| Phase | Hedging % | Speculation % | Cash % |
|-------|-----------|---------------|--------|
| Acute Crisis | 7-10% | 1-2% | 20% |
| Simmering Tensions | 3-5% | 1-2% | 15% |
| Recovery Phase | 2-3% | 3-5% | 15% |

---

## VSC CoPilot Agent Prompt

Below is the prompt to feed to your VSC CoPilot agent for updating your trading bot:

---

```
# Trading Bot Update: Geopolitical Event Options Strategy

## Objective
Update the trading bot to implement a geopolitical event options trading strategy. The bot should manage both defensive (put) and opportunistic (call) positions based on VIX regime detection, with strict risk management rules.

## Configuration Constants

```python
# Risk Management Parameters
MAX_RISK_PER_TRADE = 0.03  # 3% of portfolio per trade
MAX_TOTAL_OPTIONS_EXPOSURE = 0.20  # 20% of portfolio
HEDGE_ALLOCATION_MAX = 0.10  # 10% of protected capital
SPECULATIVE_ALLOCATION_MAX = 0.03  # 3% per speculative position
CASH_RESERVE_MIN = 0.15  # 15% minimum cash

# Exit Parameters
STOP_LOSS_THRESHOLD = 0.50  # Exit at 50% loss
PROFIT_TAKE_THRESHOLD = 1.00  # Take 50% off at 100% gain
PROFIT_TAKE_PERCENTAGE = 0.50  # Close half at profit target
MIN_DTE_CLOSE = 7  # Close positions with 7 or fewer DTE
ROLL_DTE_THRESHOLD = 45  # Consider rolling at 45 DTE if profitable

# VIX Regime Thresholds
VIX_COMPLACENCY = 15
VIX_NORMAL_LOW = 15
VIX_NORMAL_HIGH = 20
VIX_ELEVATED_HIGH = 30
VIX_PEAK_FEAR = 30
```

## Symbol Universe Definition

```python
# Defensive Put Universe
PUT_UNIVERSE = {
    "SPY": {"strike_otm_pct": (0.05, 0.10), "dte_range": (30, 60), "type": "index"},
    "QQQ": {"strike_otm_pct": (0.00, 0.10), "dte_range": (30, 45), "type": "index"},
    "IWM": {"strike_otm_pct": (0.05, 0.10), "dte_range": (30, 60), "type": "index"},
    "XLF": {"strike_otm_pct": (0.10, 0.15), "dte_range": (60, 90), "type": "sector"},
    "EEM": {"strike_otm_pct": (0.05, 0.10), "dte_range": (30, 90), "type": "region"},
    "TLT": {"strike_otm_pct": (0.05, 0.10), "dte_range": (60, 120), "type": "bond"},
    "NVDA": {"strike_otm_pct": (0.00, 0.10), "dte_range": (30, 60), "type": "stock"},
    "AAPL": {"strike_otm_pct": (0.05, 0.10), "dte_range": (60, 90), "type": "stock"},
    "TSLA": {"strike_otm_pct": (0.10, 0.20), "dte_range": (30, 60), "type": "stock"}
}

# Opportunistic Call Universe
CALL_UNIVERSE = {
    "GLD": {"strike_otm_pct": (-0.05, 0.00), "dte_range": (60, 180), "type": "safe_haven"},
    "VIX": {"strike_absolute": (25, 30), "dte_range": (30, 60), "type": "volatility"},
    "LMT": {"strike_otm_pct": (0.00, 0.10), "dte_range": (60, 180), "type": "defense"},
    "RTX": {"strike_otm_pct": (0.00, 0.10), "dte_range": (60, 180), "type": "defense"},
    "TDY": {"strike_otm_pct": (0.00, 0.10), "dte_range": (60, 180), "type": "defense"},
    "AIR": {"strike_otm_pct": (0.00, 0.10), "dte_range": (60, 180), "type": "defense"},
    "USO": {"strike_otm_pct": (0.10, 0.15), "dte_range": (60, 120), "type": "energy"},
    "TLT": {"strike_otm_pct": (0.00, 0.05), "dte_range": (60, 120), "type": "safe_haven"},
    "XLE": {"strike_otm_pct": (0.05, 0.10), "dte_range": (60, 180), "type": "energy"},
    "IWM": {"strike_otm_pct": (0.05, 0.10), "dte_range": (60, 120), "type": "recovery"},
    "EEM": {"strike_otm_pct": (0.00, 0.10), "dte_range": (90, 180), "type": "recovery"}
}
```

## Core Functions to Implement

### 1. VIX Regime Detection
```python
def get_vix_regime(current_vix: float) -> str:
    """
    Determine market regime based on VIX level.
    
    Returns:
        'complacency' - VIX below 15: Increase hedging, buy protection
        'normal' - VIX 15-20: Maintain baseline positioning
        'elevated' - VIX 20-30: Selective hedging, volatility harvesting
        'peak_fear' - VIX above 30: Reduce hedges, sell volatility
    """
    pass
```

### 2. Position Sizing Calculator
```python
def calculate_position_size(
    portfolio_value: float,
    option_premium: float,
    risk_percentage: float = 0.03,
    position_type: str = "hedge"  # or "speculative"
) -> int:
    """
    Calculate number of contracts based on risk parameters.
    
    Formula: (Portfolio Value × Risk Percentage) / (Option Premium × 100)
    
    Constraints:
    - Hedge positions: max 10% of protected capital
    - Speculative positions: max 3% per position
    - Total exposure: max 20% of portfolio
    """
    pass
```

### 3. Strike Selection Logic
```python
def select_strike(
    symbol: str,
    current_price: float,
    option_type: str,  # "put" or "call"
    universe: dict
) -> float:
    """
    Select optimal strike price based on symbol configuration.
    
    For puts: Calculate strike as current_price × (1 - otm_pct)
    For calls: Calculate strike as current_price × (1 + otm_pct)
    Special case for VIX: Use absolute strike values (25-30)
    
    Round to nearest available strike on options chain.
    """
    pass
```

### 4. Expiration Selection Logic
```python
def select_expiration(
    symbol: str,
    universe: dict,
    available_expirations: list
) -> datetime:
    """
    Select optimal expiration within configured DTE range.
    
    Prefer expirations in middle of range for balanced theta decay.
    Avoid weekly expirations unless within 7 DTE of monthly.
    """
    pass
```

### 5. Entry Signal Detection
```python
def check_put_entry_signals(
    vix_level: float,
    portfolio_beta: float,
    existing_hedge_pct: float
) -> bool:
    """
    Evaluate conditions for protective put entry.
    
    Entry conditions (any True triggers evaluation):
    - VIX below 15 AND existing_hedge_pct below 5%
    - Portfolio beta exceeds 1.0 AND existing_hedge_pct below 7%
    """
    pass

def check_call_entry_signals(
    vix_level: float,
    vix_change_pct: float,
    symbol: str,
    symbol_type: str
) -> bool:
    """
    Evaluate conditions for opportunistic call entry.
    
    Entry conditions by type:
    - safe_haven (GLD, TLT): VIX above 20 OR gold breaking out
    - volatility (VIX): VIX below 18 for asymmetric spike play
    - defense (LMT, RTX, TDY, AIR): Always evaluate if allocation permits
    - energy (USO, XLE): VIX spike + geopolitical supply catalyst
    - recovery (IWM, EEM): VIX declining from above 25
    """
    pass
```

### 6. Exit Management
```python
def evaluate_exit_conditions(
    position: dict,
    current_price: float,
    current_vix: float,
    days_to_expiration: int
) -> tuple[bool, str]:
    """
    Evaluate all exit conditions for a position.
    
    Returns: (should_exit: bool, reason: str)
    
    Exit triggers (priority order):
    1. DTE <= 7: Full exit ("min_dte")
    2. Loss >= 50%: Full exit ("stop_loss")
    3. Gain >= 100%: Partial exit 50% ("profit_take")
    4. VIX calls with VIX spike 50%+ above entry: Full exit ("vix_profit")
    5. Protective puts with 50%+ premium decline: Full exit ("hedge_reduce")
    6. DTE <= 45 AND profitable: Flag for roll consideration ("roll_candidate")
    """
    pass
```

### 7. Portfolio Allocation Manager
```python
def get_allocation_limits(crisis_phase: str) -> dict:
    """
    Return allocation limits based on crisis phase.
    
    Phases and limits:
    - 'acute': {"hedging": 0.10, "speculation": 0.02, "cash": 0.20}
    - 'simmering': {"hedging": 0.05, "speculation": 0.02, "cash": 0.15}
    - 'recovery': {"hedging": 0.03, "speculation": 0.05, "cash": 0.15}
    """
    pass

def check_allocation_capacity(
    portfolio_value: float,
    existing_positions: list,
    position_type: str,
    crisis_phase: str
) -> float:
    """
    Calculate remaining allocation capacity for position type.
    
    Returns available capital for new positions of this type.
    """
    pass
```

### 8. Order Execution Rules
```python
def create_limit_order(
    symbol: str,
    option_type: str,
    strike: float,
    expiration: datetime,
    contracts: int,
    bid: float,
    ask: float
) -> dict:
    """
    Create limit order with proper pricing.
    
    Rules:
    - Start at midpoint of bid-ask
    - Max acceptable spread: 5% of option price
    - Never use market orders
    - For positions > 100 contracts, split into tranches
    """
    pass
```

## Main Loop Logic

```python
def main_strategy_loop():
    """
    Main execution loop - run on configured interval (suggested: 15 min during market hours)
    
    Sequence:
    1. Fetch current VIX level
    2. Determine VIX regime
    3. Determine crisis phase based on regime + position count
    4. For each existing position:
       a. Evaluate exit conditions
       b. Execute exits as needed
    5. Calculate current allocation by type
    6. If PUT entry signals active AND hedge allocation available:
       a. Iterate PUT_UNIVERSE
       b. Select candidates based on regime
       c. Size positions
       d. Execute entries
    7. If CALL entry signals active AND speculative allocation available:
       a. Iterate CALL_UNIVERSE  
       b. Select candidates based on type and regime
       c. Size positions
       d. Execute entries
    8. Log all actions and portfolio state
    """
    pass
```

## Data Requirements

The bot needs access to:
- Real-time VIX quotes
- Options chains for all symbols in PUT_UNIVERSE and CALL_UNIVERSE
- Current portfolio value and positions
- Historical VIX data (for regime change detection)
- Order execution API

## Logging Requirements

Log the following on each cycle:
- Current VIX level and regime
- Crisis phase determination
- Each position evaluated with exit status
- Each entry signal evaluated with result
- All orders placed with fill status
- Portfolio allocation summary

## Testing Checklist

Before deployment, verify:
- [ ] VIX regime detection returns correct regime at boundary values (14.99, 15.01, 19.99, 20.01, 29.99, 30.01)
- [ ] Position sizing never exceeds MAX_RISK_PER_TRADE
- [ ] Total options exposure calculation correct
- [ ] Stop-loss triggers at exactly 50% loss
- [ ] Profit-take closes exactly 50% of position at 100% gain
- [ ] Positions close at 7 DTE regardless of P/L
- [ ] VIX calls have special strike handling (absolute values not OTM%)
- [ ] Limit orders use midpoint pricing
- [ ] Allocation limits respect crisis phase adjustments
```

---

This prompt provides your CoPilot agent with complete specifications derived exclusively from the attached research report. The strategy incorporates the exact symbols, strike selections, DTE ranges, position sizing rules, and exit criteria documented in the source material.