# Architecture Overview

This document provides a detailed, AI-optimized description of the trading bot’s modular architecture. It is designed to help developers or automated systems quickly understand component relationships, data flow, and extension points for programmatic reasoning, testing, and enhancement.

## 1. High-Level Design Principles

The architecture adheres to the following core principles:

*   **Modularity & Single Responsibility**: Each component (`src/*.py` module) focuses on a distinct concern (e.g., configuration, data ingestion, indicator computation, AI inference, risk management, broker interaction, or overall orchestration). This separation simplifies development, testing, and maintenance.
*   **Clear Interfaces**: Functions and methods within each module are designed with explicit, type-hinted arguments and return values. This facilitates automated parsing, static analysis, and reliable integration.
*   **Testability**: The emphasis on pure functions (especially in `indicators.py`) and well-defined side-effect boundaries (e.g., `BrokerAPI` for external calls) enables comprehensive unit and integration testing.
*   **Extensibility**: The system is designed for extension. Plugin hooks in `TradingBot` and the ability to interchange submodules (e.g., different AI clients, broker APIs, or risk metrics) allow for customization without modifying core logic.
*   **Separation of Concerns**: Key operational aspects such as configuration management, data handling (historical and real-time), technical indicator calculation, AI-based prediction, risk control, and broker communication are encapsulated in their respective modules.

## 2. Directory & File Layout

The project follows a standard Python project structure:

```text
project_root/
├── config.json                 # Main configuration settings
├── requirements.txt            # Python package dependencies
├── README.md                   # Project overview and quick start
│
├── data/
│   └── historical/
│       └── {SYMBOL}_1min.csv   # Historical 1-minute OHLCV data for backtesting
│
├── scripts/
│   └── generate_sample_csv.py  # Utility to create sample CSV data
│
├── src/                        # Core source code modules (Python package)
│   ├── __init__.py             # Marks 'src' as a Python package
│   ├── config.py               # Configuration loading and validation
│   ├── utils.py                # Utility functions (e.g., market hours)
│   ├── indicators.py           # Pure functions for technical indicator calculations
│   ├── data_handler.py         # Manages historical data and real-time tick aggregation
│   ├── ai_client.py            # Wraps external AI model endpoint communication
│   ├── risk_manager.py         # Handles position sizing, P&L, and risk limits
│   ├── broker_api.py           # Abstracts broker (Kiwoom) API interactions
│   └── trading_bot.py          # Main orchestration logic for trading operations
│
└── tests/                      # Automated tests
    ├── indicators_test.py      # Unit tests for indicators.py
    ├── ai_client_test.py       # Unit tests for ai_client.py (mocking external calls)
    ├── risk_manager_test.py    # Unit tests for risk_manager.py
    └── backtest_integration_test.py # End-to-end integration tests for backtesting
```
Further details on setting up and running the bot can be found in the [Usage Guide](Usage.md).

## 3. Module-by-Module Breakdown

This section details the responsibility, key attributes, and primary interfaces of each core module in `src/`.

### 3.1. `config.py`
*   **Responsibility**: Loads configuration settings from `config.json`, validates them, and provides them as typed attributes. It also holds a reference to the `DataHandler` instance (`_data_handler_ref`) for specific lookups (e.g., ATR for risk calculations).
*   **Key Attributes (Examples from `config.json`)**:
    *   Broker credentials: `kiwoom_id`, `kiwoom_pw`, `kiwoom_cert`, `kiwoom_account`
    *   AI model details: `ai_endpoint`, `ai_api_key`, `ai_max_retries`, `ai_request_timeout`
    *   Trading parameters: `mode` ("live" or "backtest"), `symbols` (list), `time_zone`, `initial_capital`
    *   Risk & indicator settings: `max_position_pct`, `atr_stop_multiplier`, `ema_short_period`, etc.
    *   Operational settings: `historical_lookback_days`, `loop_interval_sec`, `broker_rate_limit_sec`, `log_level`, `log_file`
*   **Primary Interface**:
    *   `Config.load_from_file(path: str) -> Config`: Static method to load and return a `Config` instance.
    *   `config._data_handler_ref: Optional[DataHandler]`: Attribute assigned post-instantiation by `TradingBot`.

### 3.2. `utils.py`
*   **Responsibility**: Provides utility functions, primarily for determining market (e.g., NYSE) open and close times based on current UTC time and the market's timezone.
*   **Key Functions**:
    *   `is_nyse_open(now_utc: datetime, market_tz: pytz.BaseTzInfo) -> bool`
    *   `is_nyse_close(now_utc: datetime, market_tz: pytz.BaseTzInfo) -> bool`
*   **Usage**: `TradingBot` uses these functions to manage its main operational loop (e.g., when to start processing or when to finalize and exit).

### 3.3. `indicators.py`
*   **Responsibility**: Contains pure functions for computing various technical indicators from OHLCV (Open, High, Low, Close, Volume) data. These functions take a `pandas.DataFrame` as input and return `pandas.Series` (or a tuple of Series) with calculated indicator values, indexed identically to the input DataFrame.
*   **Key Functions (Example Signatures)**:
    *   `compute_ema(df: pd.DataFrame, span: int) -> pd.Series`
    *   `compute_rsi(df: pd.DataFrame, period: int) -> pd.Series`
    *   `compute_bb(df: pd.DataFrame, period: int, dev: float) -> Tuple[pd.Series, pd.Series, pd.Series]` (for upper band, lower band, middle band)
    *   `compute_vwap(df: pd.DataFrame) -> pd.Series`
    *   `compute_atr(df: pd.DataFrame, period: int) -> pd.Series`
*   **Notes**: Utilizes the `ta` library for robust indicator calculations. Designed for determinism and easy unit testing.

### 3.4. `data_handler.py`
*   **Responsibility**: Manages all aspects of market data. This includes loading historical 1-minute bar data (from CSVs for backtesting or via Kiwoom API for live mode), ingesting and aggregating real-time ticks into minute bars, and invoking `indicators.py` functions to compute technical indicators on the managed data.
*   **Key Attributes**:
    *   `config: Config`: Reference to the global configuration.
    *   `mode: str`: Operational mode ("live" or "backtest").
    *   `time_zone: pytz.timezone`: The market's primary timezone (e.g., "America/New_York").
    *   `historical_data: Dict[str, pd.DataFrame]`: A dictionary mapping symbols to DataFrames containing OHLCV data and all computed indicators.
    *   `real_time_buffer: Dict[str, Dict[datetime, List[dict]]]`: Buffers incoming real-time ticks before they are aggregated into minute bars.
    *   `last_timestamp: Dict[str, Optional[datetime]]`: Tracks the timestamp of the most recently finalized minute bar for each symbol.
    *   `kiwoom: Optional[Kiwoom]`: Kiwoom API instance (used in "live" mode on Windows).
*   **Core Methods**:
    *   `fetch_historical(symbol: str) -> pd.DataFrame`: Orchestrates loading of historical data.
    *   `update_historical_all() -> None`: Loads historical data for all configured symbols.
    *   `_load_from_csv(symbol: str) -> pd.DataFrame`: Loads data from a CSV file.
    *   `_fetch_historical_kiwoom(symbol: str) -> pd.DataFrame`: Fetches data using Kiwoom API.
    *   `update_realtime(symbol: str, new_tick: dict) -> None`: Processes an incoming real-time tick.
    *   `_finalize_minute_bar(symbol: str, minute_ts: datetime) -> None`: Aggregates buffered ticks for a given minute into a new bar, appends it to `historical_data`, and triggers re-computation of indicators.
    *   `_prune_old_bars(symbol: str) -> None`: Manages the historical data window to keep only relevant recent data (e.g., 3x the longest indicator period).
    *   `_compute_all_indicators(df: pd.DataFrame) -> pd.DataFrame`: Applies all configured indicator functions from `indicators.py` to the given DataFrame.
    *   `compute_indicators(symbol: str) -> pd.DataFrame`: Returns a copy of the latest historical data (including indicators) for a symbol, typically used by `TradingBot` for signal generation.

### 3.5. `ai_client.py`
*   **Responsibility**: Manages communication with an external AI prediction service via a REST API. It sends features extracted from market data and receives predictions (e.g., expected next-minute return). Includes logic for retries with exponential backoff on transient network errors.
*   **Key Attributes**:
    *   `config: Config`: For API endpoint, key, and retry parameters.
    *   `endpoint: str`, `api_key: str`
    *   `max_attempts: int`, `timeout: float`
*   **Primary Method**:
    *   `predict(symbol: str, features: Dict[str, List[float]]) -> float`: Constructs a JSON payload, sends an HTTP POST request, handles responses (including errors and retries), and returns the parsed prediction (defaulting to 0.0 on failure).

### 3.6. `risk_manager.py`
*   **Responsibility**: Implements all risk management logic. This includes calculating position sizes (volatility-adjusted using ATR or fallback to percent-based), tracking open positions, managing account equity and available cash, recording trade history, enforcing daily profit targets, and applying daily maximum drawdown limits.
*   **Key Classes**:
    *   `Position`: Represents an open trade with attributes like `symbol`, `entry_price`, `quantity`, `stop_loss_price`, `take_profit_price`, `entry_time`, and `is_open`. Includes methods like `check_stop_loss()` and `check_take_profit()`.
    *   `RiskManager`: The main class for risk operations.
*   **`RiskManager` Key Attributes**:
    *   `config: Config`
    *   `capital: float`, `available_cash: float`
    *   `positions: Dict[str, Position]`
    *   `trade_history: List[dict]`
    *   `daily_starting_capital: float`
*   **`RiskManager` Core Methods**:
    *   `_get_latest_atr(symbol: str) -> Optional[float]`: Retrieves the latest ATR value for a symbol from `DataHandler` (via `config._data_handler_ref`).
    *   `calculate_position_size(symbol: str, price: float) -> Optional[Tuple[int, float, float]]`: Determines appropriate trade quantity, stop-loss price, and take-profit price based on ATR or percentage rules and current capital.
    *   `can_open_position(symbol: str, price: float) -> bool`: Checks if a new position can be opened based on available capital, max position limits, and daily drawdown status.
    *   `open_position(symbol: str, price: float) -> None`: Records a new open position and updates cash.
    *   `close_position(symbol: str, exit_price: float) -> None`: Closes an existing position, records P&L, updates capital/cash, and logs the trade.
    *   `get_equity_curve() -> pd.DataFrame`: Generates a DataFrame representing the equity over time based on trade history.
    *   `get_current_drawdown() -> float`: Calculates the current peak-to-trough drawdown as a percentage.
    *   `check_daily_targets() -> bool`: Returns `False` if daily profit target is met or max daily drawdown is breached, signaling to halt new trading.

### 3.7. `broker_api.py`
*   **Responsibility**: Abstracts direct interactions with the Kiwoom brokerage API. It provides methods for sending and canceling orders, enforcing API rate limits, validating parameters, and ensuring consistent logging. This module is specific to Kiwoom and would be replaced or augmented for other brokers.
*   **Key Classes**:
    *   `HogaType(Enum)`: Defines order types like `LIMIT` ("00") and `MARKET` ("03").
    *   `BrokerAPI`: The main class for broker interactions.
*   **`BrokerAPI` Attributes**:
    *   `kiwoom: Kiwoom`: A connected Kiwoom instance.
    *   `account_no: str`, `screen_no: str`
    *   `rate_limit_sec: float` (from `config`)
*   **`BrokerAPI` Methods**:
    *   `send_order(direction: Literal["BUY", "SELL"], symbol: str, quantity: int, price: float, order_type: HogaType = HogaType.LIMIT) -> None`: Sends an order to Kiwoom.
    *   `cancel_order(order_id: str) -> None`: (Optional) Sends an order cancellation request.

### 3.8. `trading_bot.py`
*   **Responsibility**: The central orchestrator of the trading bot. It initializes all other components, manages the main trading loop (differentiating between backtest and live modes), generates trading signals by synthesizing information from `DataHandler` and `AIClient`, executes orders via `BrokerAPI` (in live mode) or directly updates `RiskManager` (in backtest mode), and handles final cleanup. It also provides plugin hooks for extensibility.
*   **Key Attributes**:
    *   `config: Config`, `data_handler: DataHandler`, `risk_manager: RiskManager`, `ai_client: AIClient`
    *   `mode: str`
    *   `plugins: Dict[str, List[Callable]]`: Stores registered plugin callbacks for "before_signal" and "after_signal" hooks.
    *   `kiwoom: Optional[Kiwoom]`, `broker: Optional[BrokerAPI]` (for live mode)
    *   `trading_day: date`
*   **Core Methods**:
    *   `register_plugin(hook_name: str, callback: Callable) -> None`: Allows external code to register callbacks for specific events.
    *   `initialize() -> None`: Prepares the bot for operation, primarily by loading historical data.
    *   `fetch_realtime_ticks() -> None`: (Backtest only) Spawns a thread to simulate a real-time tick feed.
    *   `generate_signals(symbol: str) -> dict`: The core logic for deciding trades. It:
        1.  Retrieves the latest data and indicators from `DataHandler`.
        2.  Invokes `before_signal` plugins.
        3.  Computes various technical sub-signals (EMA crossover, RSI levels, Bollinger Band breaks, VWAP breaks).
        4.  Optionally calls `ai_client.predict()` for an AI-based prediction.
        5.  Combines these inputs into weighted scores.
        6.  Checks current position status and applies risk rules (`RiskManager.can_open_position`, SL/TP checks).
        7.  Determines the final signal: "BUY", "SELL", "SELL_SL", "SELL_TP", or "HOLD", along with price and quantity.
        8.  Invokes `after_signal` plugins.
        9.  Returns the signal dictionary.
    *   `execute_order(signal: dict, symbol: str) -> None`: Acts on the generated signal.
    *   `run() -> None`: The main entry point to start the bot's operation.
    *   `_on_receive_real_data(sRealType, sRealData) -> None`: (Live mode only) Kiwoom API callback for incoming real-time data.
    *   `_final_cleanup() -> None`: Liquidates all open positions at the end of the trading session or on interruption.

## 4. Data Flow & Interactions

1.  **Startup & Initialization**:
    *   `config.json` is loaded into a `Config` object.
    *   Core components (`DataHandler`, `RiskManager`, `AIClient`, `TradingBot`) are instantiated, with `Config` passed to them. `DataHandler` instance is referenced back in `Config`.
    *   `TradingBot.initialize()` calls `DataHandler.update_historical_all()`.
        *   `DataHandler` loads historical data (CSV or Kiwoom API), computes initial indicators, and stores it in `historical_data`.
2.  **Real-Time Data Ingestion & Bar Finalization**:
    *   **Live Mode**: Kiwoom pushes ticks to `TradingBot._on_receive_real_data`, which forwards them to `DataHandler.update_realtime()`.
    *   **Backtest Mode**: `TradingBot.fetch_realtime_ticks()` thread generates synthetic ticks and sends them to `DataHandler.update_realtime()`.
    *   `DataHandler.update_realtime()` buffers ticks. When a new minute begins, `_finalize_minute_bar()` is called for the completed minute.
    *   `_finalize_minute_bar()` aggregates ticks, creates a new OHLCV bar, appends it to `historical_data`, prunes old data, and recomputes all indicators via `_compute_all_indicators()`.
3.  **Signal Generation & Order Execution Loop** (Simplified for backtest main loop, or event-driven in live):
    *   `TradingBot.generate_signals()` is called for each symbol.
        *   It fetches the latest data+indicators from `DataHandler.compute_indicators()`.
        *   Technical rules and (optionally) AI predictions (`AIClient.predict()`) are combined.
        *   `RiskManager` (e.g., `can_open_position()`, SL/TP checks) validates potential trades.
        *   A signal dictionary (e.g., `{"signal": "BUY", "price": ..., "quantity": ...}`) is returned.
    *   If the signal is not "HOLD", `TradingBot.execute_order()` is called.
        *   **Live Mode**: `BrokerAPI.send_order()` interacts with Kiwoom. `RiskManager` is updated.
        *   **Backtest Mode**: `RiskManager` is updated directly (simulating fills).
4.  **Risk Monitoring**:
    *   `RiskManager` continuously tracks P&L, equity, and drawdown.
    *   `TradingBot` (especially in backtest) periodically calls `RiskManager.check_daily_targets()` to decide if trading should continue.
5.  **Termination & Cleanup**:
    *   The main loop ends if the market closes (`utils.is_nyse_close()`) or if daily risk limits are hit.
    *   `TradingBot._final_cleanup()` ensures all open positions are liquidated.

## 5. AI Agent-Friendly Representation (Conceptual JSON Structure)

This structured representation aids automated understanding of the system's architecture.

```json
{
  "projectGoal": "Modular AI-optimized trading bot with backtest/live capabilities.",
  "designPrinciples": ["Modularity", "Testability", "Extensibility", "SeparationOfConcerns"],
  "modules": [
    {
      "name": "config", "file": "src/config.py",
      "purpose": "Load, validate, and provide access to configuration from config.json.",
      "keyClasses": [{"name": "Config", "methods": ["load_from_file"]}]
    },
    {
      "name": "utils", "file": "src/utils.py",
      "purpose": "Provide utility functions, e.g., market open/close checks.",
      "keyFunctions": ["is_nyse_open", "is_nyse_close"]
    },
    {
      "name": "indicators", "file": "src/indicators.py",
      "purpose": "Compute technical indicators as pure functions on DataFrame inputs.",
      "keyFunctions": ["compute_ema", "compute_rsi", "compute_bb", "compute_vwap", "compute_atr"]
    },
    {
      "name": "data_handler", "file": "src/data_handler.py",
      "purpose": "Manage historical and real-time market data, and apply indicators.",
      "keyClasses": [{"name": "DataHandler", "methods": ["fetch_historical", "update_realtime", "_finalize_minute_bar", "compute_indicators"]}]
    },
    {
      "name": "ai_client", "file": "src/ai_client.py",
      "purpose": "Interface with an external AI prediction service via REST API.",
      "keyClasses": [{"name": "AIClient", "methods": ["predict"]}]
    },
    {
      "name": "risk_manager", "file": "src/risk_manager.py",
      "purpose": "Manage trading risk, including position sizing, P&L tracking, and enforcing limits.",
      "keyClasses": [
        {"name": "Position"},
        {"name": "RiskManager", "methods": ["calculate_position_size", "open_position", "close_position", "check_daily_targets"]}
      ]
    },
    {
      "name": "broker_api", "file": "src/broker_api.py",
      "purpose": "Abstract Kiwoom API interactions for order management.",
      "keyClasses": [{"name": "BrokerAPI", "methods": ["send_order", "cancel_order"]}]
    },
    {
      "name": "trading_bot", "file": "src/trading_bot.py",
      "purpose": "Orchestrate all trading operations and manage the main bot lifecycle.",
      "keyClasses": [{"name": "TradingBot", "methods": ["initialize", "generate_signals", "execute_order", "run", "_on_receive_real_data", "_final_cleanup", "register_plugin"]}]
    }
  ],
  "dependencies": {
    "TradingBot": ["Config", "DataHandler", "RiskManager", "AIClient", "BrokerAPI", "utils"],
    "RiskManager": ["Config", "DataHandler"], // DataHandler via config._data_handler_ref
    "DataHandler": ["Config", "indicators", "KiwoomSDK (conditional)"],
    "AIClient": ["Config", "requests"],
    "BrokerAPI": ["KiwoomSDK", "Config"]
    // ... etc.
  },
  "keyDataFlows": [
    "Config loading -> Component instantiation with Config",
    "Data ingestion (CSV/API) -> DataHandler.historical_data -> Indicator computation",
    "Real-time tick -> DataHandler.real_time_buffer -> Bar finalization -> Indicator update",
    "TradingBot.generate_signals (uses DataHandler.compute_indicators, AIClient.predict, RiskManager.can_open_position)",
    "TradingBot.execute_order (uses BrokerAPI (live) or RiskManager (backtest))"
  ]
}
```
**Note**: The JSON above is a conceptual, simplified representation. A more detailed, machine-parseable schema (e.g., using OpenAPI for methods, or a custom JSON schema) could be developed for deeper AI agent integration.

## 6. Execution Summaries

For detailed step-by-step guides on running the bot in backtest or live mode, please refer to the **[Usage Guide](Usage.md)**. This section provides a high-level summary of the execution flow.

### 6.1. Backtest Execution Flow
1.  **Instantiation**: Core components (`Config`, `DataHandler`, `RiskManager`, `AIClient`, `TradingBot`) are created. Historical data is loaded from CSVs by `DataHandler` and indicators are pre-computed.
2.  **Run Invocation**: `TradingBot.run()` is called.
    *   `initialize()` confirms data loading.
    *   `fetch_realtime_ticks()` starts a thread simulating ticks.
    *   The main loop begins:
        *   For each symbol, `generate_signals()` is called. If a trade is signaled, `execute_order()` updates `RiskManager`.
        *   `RiskManager.check_daily_targets()` is checked; if limits are hit, the loop breaks.
        *   `utils.is_nyse_close()` is checked; if the market is closed, the loop breaks.
        *   The loop sleeps for `config.loop_interval_sec`.
    *   `_final_cleanup()` liquidates simulated open positions.

### 6.2. Live Execution Flow (Windows + Kiwoom)
1.  **Instantiation**: Components are created. `DataHandler` connects to Kiwoom. `TradingBot` registers Kiwoom's `OnReceiveRealData` callback.
2.  **Run Invocation**: `TradingBot.run()` is called.
    *   `initialize()` loads historical data via Kiwoom API and computes indicators.
    *   The main loop starts, primarily waiting for market close (`utils.is_nyse_close()`).
    *   Trading is event-driven:
        *   Kiwoom pushes ticks to `_on_receive_real_data`.
        *   This updates `DataHandler`, which finalizes bars and recomputes indicators.
        *   If a bar is finalized, `generate_signals()` is called, potentially leading to `execute_order()` using `BrokerAPI`.
    *   `_final_cleanup()` is called upon market close to liquidate live positions.

## 7. Testing Strategy

The bot employs a multi-layered testing strategy:

*   **Unit Tests (`tests/*.py`)**:
    *   `indicators_test.py`: Verifies the correctness of individual indicator calculations using known inputs and outputs.
    *   `ai_client_test.py`: Mocks `requests.post` to test `AIClient`'s response handling, retry logic, and fallback mechanisms without actual network calls.
    *   `risk_manager_test.py`: Tests position sizing logic (ATR-based and percent-based), P&L calculations, drawdown computations, and daily target enforcement using controlled scenarios.
*   **Integration Tests (`tests/backtest_integration_test.py`)**:
    *   Performs an end-to-end run of the bot in backtest mode using a small, reproducible sample CSV (generated by `scripts/generate_sample_csv.py`).
    *   Verifies that components interact correctly, trades are generated, and P&L is updated. AI client responses can be mocked for deterministic outcomes.

This strategy ensures that individual components function as expected and that they integrate correctly to perform the overall trading task.

## 8. Extensibility and Customization

The modular design facilitates several extension points:

*   **New Indicators**: Add new functions to `indicators.py` and integrate them into `DataHandler._compute_all_indicators`.
*   **Alternative AI Models**: Subclass `AIClient` or modify `predict()` to interface with different AI services or local models (e.g., loading a TensorFlow/PyTorch model directly).
*   **Different Broker APIs**: Implement a new class similar to `BrokerAPI` for another brokerage (e.g., Interactive Brokers) and update `TradingBot` to use it based on configuration.
*   **Plugin Hooks**: Use `TradingBot.register_plugin("before_signal", ...)` or `("after_signal", ...)` to inject custom logic for logging, dynamic parameter adjustments, or alternative signal evaluation without altering core `TradingBot` code.
*   **Custom Risk Metrics**: Modify `RiskManager` to use different volatility measures or implement more sophisticated capital allocation strategies.

This document provides the foundational understanding required to extend or customize the trading bot. For specific "how-to" instructions on usage, refer to the [Usage Guide](Usage.md).