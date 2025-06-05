# System Architecture

This document describes the overall architecture of the **Automatic Trading Bot** project. It covers component responsibilities, data flows, module interactions, and deployment considerations.

------------------------------------------------------------------------

## 1. System Overview

The Automatic Trading Bot is designed to:

1.  Collect real-time tick data (per-second price + volume) for a configurable list of symbols.
2.  Aggregate ticks into 1-minute bars (OHLCV) and compute technical indicators (EMA, RSI, Bollinger Bands, VWAP).
3.  Generate intraday buy/sell signals based on a hybrid of technical rules and AI model predictions.
4.  Execute orders via Kiwoom OpenAPI (or equivalent broker API), enforcing stop-loss, take-profit, and daily risk limits.
5.  Provide comprehensive logging, backtesting support, and convenient configuration management.

Below is a high-level ASCII diagram of major components and data flows: 
# System Architecture

This document describes the overall architecture of the **Automatic Trading Bot** project. It covers component responsibilities, data flows, module interactions, and deployment considerations.

---

## 1. System Overview

The Automatic Trading Bot is designed to:

1. Collect real-time tick data (per-second price + volume) for a configurable list of symbols.
2. Aggregate ticks into 1-minute bars (OHLCV) and compute technical indicators (EMA, RSI, Bollinger Bands, VWAP).
3. Generate intraday buy/sell signals based on a hybrid of technical rules and AI model predictions.
4. Execute orders via Kiwoom OpenAPI (or equivalent broker API), enforcing stop-loss, take-profit, and daily risk limits.
5. Provide comprehensive logging, backtesting support, and convenient configuration management.

Below is a high-level Mermaid flowchart of major components and data flows. You can paste this directly into any Markdown environment that supports Mermaid to render a diagram.

```mermaid
flowchart TD
    subgraph Entry[ ]
        direction TB
        A[main.py\n• Load config.json\n• Initialize TradingBot\n• Configure logging]
    end

    subgraph Core[TradingBot]
        direction TB
        B1[initialize()\n• DataHandler.update_historical_all()\n• Kiwoom API login (TODO)\n• Determine trading_day]
        B2[fetch_realtime_ticks()\n• Start dummy thread or real API callback\n• DataHandler.update_realtime()]
        B3[run() Loop\n• For each symbol →\n  – DataHandler.compute_indicators()\n  – generate_signals()\n  – execute_order()\n• RiskManager.check_daily_targets()\n  – On limit reached, call _final_cleanup()]
    end

    subgraph ConfigModule[src/config.py]
        direction TB
        C1[Config\n• Map config.json → Python attributes\n(broker credentials, symbols, risk params, indicator settings, API URLs)]
    end

    subgraph DataModule[src/data_handler.py]
        direction TB
        D1[DataHandler\n• fetch_historical(symbol)\n  – Load N days of 1-min OHLCV (Dummy or API)\n• update_historical_all()\n• update_realtime(symbol, tick)\n  – Buffer ticks, every 60 → _aggregate_to_minute_bar()\n• compute_indicators(symbol)\n  – Calculate EMA, RSI, Bollinger Bands, VWAP]
    end

    subgraph RiskModule[src/risk_manager.py]
        direction TB
        R1[RiskManager\n• Track capital, available_cash, daily_starting_capital\n• can_open_position(symbol, price)\n  – Check position sizing, daily drawdown, cash\n• open_position(symbol, price, qty)\n  – Set SL/TP, update cash\n• close_position(symbol, exit_price)\n  – Compute P&L, update capital & cash\n• check_daily_targets()\n  – Compare return & drawdown to limits]
    end

    subgraph Indicators[Technical Indicators]
        direction TB
        I1[EMA, RSI, Bollinger Bands, VWAP\nvia `ta` library]
    end

    subgraph AIModel[External AI Model | REST API]
        direction TB
        M1[AI Prediction Endpoint\n• Returns predicted_return\n• Derive ai_buy_signal / ai_sell_signal]
    end

    subgraph BrokerAPI[Broker API (Kiwoom OpenAPI)]
        direction TB
        K1[send_order()\n• Actual BUY/SELL order submission\n• Return execution report (TODO)]
    end

    %% Connections
    A --> B1
    A --> C1
    C1 --> B1
    B1 --> B2
    B2 --> D1
    B2 --> R1
    B2 --> B3

    D1 --> I1
    I1 --> B3
    M1 --> B3
    B3 --> R1
    B3 --> K1
    R1 --> K1

    style Entry fill:#f9f,stroke:#333,stroke-width:1px
    style Core fill:#bbf,stroke:#333,stroke-width:1px
    style ConfigModule fill:#bfb,stroke:#333,stroke-width:1px
    style DataModule fill:#bff,stroke:#333,stroke-width:1px
    style RiskModule fill:#ffb,stroke:#333,stroke-width:1px
    style Indicators fill:#fbf,stroke:#333,stroke-width:1px
    style AIModel fill:#ffe,stroke:#333,stroke-width:1px
    style BrokerAPI fill:#eef,stroke:#333,stroke-width:1px
```
    
### 2. Component Responsibilities

1.  **`main.py`**
    -   Entry point of the application.\
    -   Loads `config.json` (via `utils.load_json`) and configures logging.\
    -   Instantiates `TradingBot(config_dict)` and calls `initialize()` and `run()`.\
    -   Catches `KeyboardInterrupt` and unexpected exceptions to ensure proper cleanup.
2.  **`src/config.py`**
    -   Defines a `Config` class that maps JSON keys (from `config.json`) and environment variables into Python attributes.\
    -   Attributes include broker credentials, AI API endpoint, symbol list, time zone, capital/risk parameters, and indicator settings.\
    -   Ensures all numeric values (percentages, intervals) are converted to the correct Python types (`float`, `int`).
3.  **`src/data_handler.py`**
    -   **`DataHandler`** class is responsible for:
        -   **Historical Data Fetching**: `fetch_historical(symbol)` returns a `pandas.DataFrame` of date-indexed OHLCV bars for the last `historical_lookback_days`.
            -   In production, this should connect to Kiwoom OpenAPI’s historical data TR (transaction requests) or an external data provider (AlphaVantage, IEX, etc.).\
        -   **Real-time Tick Buffering**: Receives tick events (per second), appends to `real_time_buffer[symbol]`, and once 60 ticks have accumulated, calls `_aggregate_to_minute_bar(symbol)` to produce a 1-minute bar.\
        -   **Indicator Calculation**: `compute_indicators(symbol)` computes:
            -   EMA (short/long) via `ta.trend.EMAIndicator`\
            -   RSI via `ta.momentum.RSIIndicator`\
            -   Bollinger Bands via `ta.volatility.BollingerBands`\
            -   VWAP as a cumulative (price × volume) / cumulative volume (minute-by-minute)\
        -   **Data Caching**: Maintains `historical_data[symbol]` (DataFrame) and `last_timestamp[symbol]`. Enables quick lookup during each loop iteration.
4.  **`src/risk_manager.py`**
    -   **`Position`** class holds details for each open position:
        -   `symbol`, `entry_price`, `quantity`, `stop_loss_price`, `take_profit_price`, and an `is_open` flag.\
        -   Methods:
            -   `check_stop_loss(current_price)` returns `True` if `current_price <= stop_loss_price`.\
            -   `check_take_profit(current_price)` returns `True` if `current_price >= take_profit_price`.\
    -   **`RiskManager`** class manages:
        -   `capital`: current account equity (float).\
        -   `available_cash`: free cash available to open new positions.\
        -   `positions`: dict mapping `symbol` → `Position` instance (only open positions).\
        -   `daily_starting_capital`: used to measure daily return/drawdown.\
    -   Core methods:
        -   `can_open_position(symbol, price) → bool`:
            1.  Calculates current invested capital across open positions.\
            2.  Ensures that `price * 1` does not exceed `capital * max_position_pct`.\
            3.  Checks whether `(daily_starting_capital − capital) / daily_starting_capital < daily_max_loss_pct / 100`.\
            4.  Verifies that `price * 1 <= available_cash`.\
        -   `open_position(symbol, price, quantity)`:
            1.  Calculates `sl_price = price * (1 − stop_loss_pct/100)`.\
            2.  Calculates `tp_price = price * (1 + take_profit_pct/100)`.\
            3.  Creates a new `Position` and deducts `price × quantity` from `available_cash`.\
        -   `close_position(symbol, exit_price)`:
            1.  Locates `Position`, calculates `profit = (exit_price − entry_price) × quantity`.\
            2.  Increments `capital` by `profit`, increments `available_cash` by `exit_price × quantity`.\
            3.  Marks `Position.is_open = False`.\
        -   `check_daily_targets() → bool`:
            1.  Computes `current_return = (capital − daily_starting_capital) / daily_starting_capital`.\
            2.  If `current_return ≥ target_daily_return_pct/100`, returns `False`.\
            3.  Computes `current_drawdown = (daily_starting_capital − capital) / daily_starting_capital`.\
            4.  If `current_drawdown ≥ daily_max_loss_pct/100`, returns `False`.\
            5.  Otherwise returns `True`.
5.  **`src/trading_bot.py`**
    -   **`TradingBot`** orchestrates the entire intraday trading process. Responsibilities:
        1.  **Initialization** (`initialize()`):
            -   Calls `data_handler.update_historical_all()` to pre-load historical bars for each symbol.\
            -   Performs Kiwoom API login (placeholder/TODO).\
            -   Determines `trading_day` by converting UTC → configured time zone (e.g., `"America/New_York"`) via `pytz`.\
        2.  **Real-time Tick Retrieval** (`fetch_realtime_ticks()`):
            -   In production, this logic should be replaced by Kiwoom OpenAPI’s `OnReceiveRealData` callback, which triggers `data_handler.update_realtime(symbol, tick_dict)`.\
            -   In this template, a daemon thread (`_dummy_tick_feed()`) generates random ticks per second for each symbol.\
        3.  **Signal Generation** (`generate_signals(symbol)`):
            -   Retrieves `df = data_handler.compute_indicators(symbol)`.\

            -   Requires at least `max(ema_long_period, rsi_period, bb_period)` rows; otherwise returns `{ "signal": "HOLD" }`.\

            -   Reads latest row (index −1) as `latest`, previous row as `prev`.\

            -   Computes:

                -   **EMA crossover**:
                    -   `ema_cross_up = prev.ema_short < prev.ema_long && latest.ema_short > latest.ema_long`\
                    -   `ema_cross_down = prev.ema_short > prev.ema_long && latest.ema_short < latest.ema_long`\
                -   **RSI signals**:
                    -   `rsi_oversold = latest.rsi < rsi_oversold`\
                    -   `rsi_overbought = latest.rsi > rsi_overbought`\
                -   **Bollinger Breakout**:
                    -   `bb_break_up = prev.close <= prev.bb_hband && latest.close > latest.bb_hband`\
                    -   `bb_break_down = prev.close >= prev.bb_lband && latest.close < latest.bb_lband`\
                -   **VWAP Breakout**:
                    -   `vwap_break_up = prev.close <= prev.vwap && latest.close > latest.vwap`\
                    -   `vwap_break_down = prev.close >= prev.vwap && latest.close < latest.vwap`\
                -   **AI prediction** (placeholder):
                    -   In production, perform a `POST` to `ai_endpoint` with recent features, read `predicted_return`.\
                    -   Here: `predicted_return = np.random.uniform(-0.01, +0.01)`.\
                    -   `ai_buy_signal = predicted_return > 0.005`\
                    -   `ai_sell_signal = predicted_return < -0.005`\

            -   Combines weighted scores:

                ```         
                buy_score  = (ema_cross_up ? 1.0 : 0)
                           + (rsi_oversold ? 0.5 : 0)
                           + (bb_break_up ? 0.7 : 0)
                           + (vwap_break_up ? 0.5 : 0)
                           + (ai_buy_signal ? 1.0 : 0)

                sell_score = (ema_cross_down ? 1.0 : 0)
                           + (rsi_overbought ? 0.5 : 0)
                           + (bb_break_down ? 0.7 : 0)
                           + (vwap_break_down ? 0.5 : 0)
                           + (ai_sell_signal ? 1.0 : 0)
                ```

            -   Thresholds (tunable):

                ```         
                BUY_THRESHOLD  = 1.5
                SELL_THRESHOLD = 1.5
                ```

            -   Checks if symbol already has an open position (`has_position = symbol in risk_manager.positions and is_open`).\

            -   **Buy condition**:

                ```         
                if (buy_score ≥ BUY_THRESHOLD)
                   and (not has_position)
                   and risk_manager.can_open_position(symbol, price):
                       quantity = int((capital * max_position_pct) // price)
                       if quantity ≥ 1: return { "signal": "BUY", "price": price, "quantity": quantity }
                ```

            -   **Sell condition**:

                ```         
                if has_position and (sell_score ≥ SELL_THRESHOLD): return { "signal": "SELL", "price": price, "quantity": 0 }
                ```

            -   **Stop-loss/Take-profit override**:

                ```         
                if has_position:
                  pos = risk_manager.positions[symbol]
                  if pos.check_stop_loss(price): return { "signal": "SELL_SL", "price": price, "quantity": 0 }
                  if pos.check_take_profit(price): return { "signal": "SELL_TP", "price": price, "quantity": 0 }
                ```

            -   Otherwise: `{ "signal": "HOLD" }`.\
        4.  **Order Execution** (`execute_order(signal, symbol)`):
            -   Reads `signal_type = signal["signal"]`.\
            -   If `"BUY"`, calls `risk_manager.open_position(symbol, price, quantity)` (replace with actual `kiwoom.send_order`).\
            -   If `"SELL"`, `"SELL_SL"`, or `"SELL_TP"`, calls `risk_manager.close_position(symbol, price)` (replace with actual `kiwoom.send_order`).\
            -   All actual API calls (Kiwoom) are marked as `TODO`.\
        5.  **Main Running Loop** (`run()`):
            -   Calls `fetch_realtime_ticks()` (starts dummy thread or sets up real callback).\

            -   Enters `while True` loop:

                ```         
                now_utc = datetime.utcnow()
                if not is_market_open(now_utc):
                    sleep(60)  # Re-check after 1 minute
                    continue

                for symbol in config.symbols:
                    df = data_handler.historical_data[symbol]
                    if df.empty: continue
                    signal = generate_signals(symbol)
                    if signal["signal"] ≠ "HOLD":
                        execute_order(signal, symbol)

                if not risk_manager.check_daily_targets():
                    break  # Stop new entries, then finalize

                sleep(loop_interval_sec)
                ```

            -   After loop (either market closed or daily target reached), calls `_final_cleanup()` to close all open positions at last available price.\
        6.  **Market Open Check** (`is_market_open(now_utc)`)
            -   Converts `now_utc` to hours/minutes; for simplicity assumes UTC 14:30–21:00 = NYSE open (does not account for daylight savings).\
            -   In production, use `pytz` or a market-calendar library (e.g., `pandas_market_calendars`) to accurately detect open/close times including holidays.\
        7.  **Final Cleanup** (`_final_cleanup()`)
            -   Iterates through `risk_manager.positions`, and for each `pos.is_open == True`, retrieves `last_price = data_handler.historical_data[symbol].close.iloc[-1]` and calls `risk_manager.close_position(symbol, last_price)`.
6.  **`src/utils.py`**
    -   Provides helper functions that are used across modules:
        -   `load_json(path) → dict`: Safely opens a file, parses JSON, returns a `dict`.\
        -   `save_log(message, log_file)`: Appends `timestamp + message` to a text log.\
        -   `ensure_dir(directory)`: Creates a directory (and parents) if it does not already exist.

------------------------------------------------------------------------

## 3. Data Flow and Interactions

1.  **Application Start**
    -   `main.py` reads `config.json` → instantiates `TradingBot(config_dict)` → calls `initialize()`.\
    -   `initialize()` calls `data_handler.update_historical_all()` to preload historical bars and then logs in to Kiwoom.
2.  **Real-Time Tick Loop**
    -   Real tick events arrive via Kiwoom OpenAPI callbacks (or dummy thread). Each tick is a structure:

        ``` jsonc
        {
          "datetime": "2025-06-05T13:00:00.123Z",
          "price": 128.45,
          "volume": 50
        }
        ```

    -   For each tick, `data_handler.update_realtime(symbol, tick)` appends to `real_time_buffer[symbol]`. Once 60 ticks are collected, `_aggregate_to_minute_bar(symbol)` aggregates into a 1-minute bar which is appended to `historical_data[symbol]`.
3.  **Indicator Calculation**
    -   On each loop iteration, for each symbol:
        -   `TradingBot.generate_signals(symbol)` calls `data_handler.compute_indicators(symbol)`.\
        -   `compute_indicators` recalculates EMA, RSI, Bollinger, VWAP on the up-to-date DataFrame.
4.  **Signal Generation & Order Execution**
    -   `generate_signals` returns a `{"signal": X, "price": P, "quantity": Q}` dictionary.\
    -   `execute_order` interprets that dictionary, updates account/position state in `risk_manager`, and (in production) would submit orders via Kiwoom API.
5.  **Risk Management**
    -   Every cycle, after orders (if any), `TradingBot.run()` calls `risk_manager.check_daily_targets()`.\
    -   If daily profit ≥ target or drawdown ≥ limit, new entries are blocked and loop ends.
6.  **Final Cleanup**
    -   Once main loop exits, `TradingBot._final_cleanup()` force-closes all open positions at the last known close price.

------------------------------------------------------------------------

## 4. Deployment & Execution Environment

1.  **Dependencies**
    -   Python 3.8 or higher\

    -   Required packages (in `requirements.txt`):

        ```         
        pandas>=1.3.0
        numpy>=1.21.0
        ta>=0.8.0
        pytz>=2021.3
        requests>=2.26.0
        python-dotenv>=0.19.0
        PyKiwoom>=1.4.4
        pytest>=6.2.0
        ```

    -   Kiwoom OpenAPI (HTS) installed locally, with proper digital certificate set.
2.  **Configuration**
    -   `config.json` holds all environment-specific settings: broker credentials, symbols, risk parameters, indicator parameters, API endpoints, logging locations.\
    -   Sensitive values (passwords, API keys) may be overridden by environment variables (via `python-dotenv` and a `.env` file).
3.  **Logging**
    -   Logs written to `logs/bot.log` (rotating logs or log rollover can be added).\
    -   `log_level` configured in `config.json`; typically `"INFO"` or `"DEBUG"`.
4.  **Backtesting vs. Live Trading**
    -   The same codebase can run in **live mode** (real ticks, real API orders) or **backtest mode** (historical CSV data, no real orders).\
    -   To support backtesting, you would:
        1.  Populate `data/historical/` with one or more CSV/Parquet files named `{SYMBOL}_1min.csv`.\
        2.  Modify or extend `TradingBot.run()` to iterate over historical timestamps instead of real clock, feeding `DataHandler` one bar at a time.\
        3.  Disable actual `execute_order` API calls and instead record simulated P&L.
5.  **Scalability Considerations**
    -   For a small list of symbols (≤ 10), a single process is sufficient.\
    -   For hundreds of symbols or ultra-high-frequency ticks, consider:
        -   Asynchronous I/O (e.g., `asyncio`), nonblocking HTTP calls for AI model.\
        -   External queue/broker (Redis, Kafka) to buffer ticks.\
        -   Horizontal scaling: run multiple bots on different symbol subsets.\
    -   Use a database (PostgreSQL, InfluxDB) to store historical ticks/indicators if persistence or large-scale analytics is required.

------------------------------------------------------------------------

## 5. Future Enhancements

1.  **Accurate Market Calendar**
    -   Replace the simplified `is_market_open` logic with a robust market-calendar library (e.g., `pandas_market_calendars`) to handle holidays, half-days, daylight-savings.
2.  **Modular AI Integration**
    -   Extract AI model code into a separate `ai_model.py` module.\
    -   Implement streaming or batch predictions (e.g., gRPC, WebSockets for sub-second latency).\
    -   Allow multiple AI models (LSTM, Transformer, RL) and dynamically select or ensemble outputs.
3.  **Order Execution Resilience**
    -   Add retry logic in `execute_order` for network timeouts or API rate limits.\
    -   Monitor for partial fills, slippage, and adjust `quantity` or price accordingly.
4.  **Metric Dashboards**
    -   Expose a simple web dashboard (Flask/Streamlit) to display:
        -   Real-time P&L, current positions, indicator charts per symbol.\
        -   Daily/weekly performance metrics, drawdown, Sharpe ratio.
5.  **Containerization & CI/CD**
    -   Create a `Dockerfile` that installs dependencies and runs `main.py`.\
    -   Use GitHub Actions (or GitLab CI) to run `pytest` on every push/PR.\
    -   Automate builds and deployments to a cloud VM or Kubernetes cluster.

------------------------------------------------------------------------

## 6. Summary

-   The `docs/architecture.md` file outlines each module’s role, data flow diagrams, and interactions.\
-   It also highlights how historical data and real-time ticks feed into indicator calculation, which in turn drives signal generation.\
-   The `TradingBot` class is the orchestrator that ties together data ingestion, indicator computation, decision logic, order execution, and risk enforcement.

With this architecture, you have a clear separation of concerns that facilitates maintainability, extensibility, and robust intraday trading operations.
