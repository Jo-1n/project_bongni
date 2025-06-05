# Usage Guide

This document describes how to run, configure, and monitor the trading bot in both backtest and live modes. Follow these steps to get the bot up and running, and refer to configuration details in `config.json`.

## 1. Prerequisites

### Python Environment

Ensure Python 3.9 or newer is installed.

Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate       # macOS/Linux
venv\Scripts\activate        # Windows
```

### Install Dependencies

Install required packages from `requirements.txt`:
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Directory Layout

Ensure your project root directory contains essential files and folders as outlined in the `README.md`. Key items you will interact with include:
*   `config.json`: For bot configuration.
*   `data/historical/`: For storing CSV data for backtesting.
*   `src/trading_bot.py`: The main script to run the bot.
*   `scripts/generate_sample_csv.py`: For creating sample data.

For a full directory structure, refer to `README.md` or `docs/architecture.md`.

### KIWOOM OpenAPI (Live Mode Only)

If you plan to run in **live mode**, you must be on a **Windows** machine with the Kiwoom OpenAPI+ and `pykiwoom` library installed.

1.  **Kiwoom OpenAPI+ Setup**: Download and install the official Kiwoom HTS (OpenAPI+) program from the Kiwoom website and ensure your account is properly set up and accessible.
2.  **Install `pykiwoom`**:
    ```bash
    pip install pykiwoom
    ```
3.  **Verify Connection**: Test if `pykiwoom` can connect to the Kiwoom API by running a simple Python script or using the REPL (see Kiwoom/`pykiwoom` documentation for connection examples).

## 2. Configuring `config.json`

The bot's behavior is primarily controlled by the `config.json` file located in the project root.

### Copy Example Configuration

If a `config.example.json` file is present in the repository, duplicate it and rename the copy to `config.json`. Otherwise, create `config.json` from scratch based on the fields below.

### Key Configuration Fields

*   **`mode`**: `String`. Must be either `"backtest"` or `"live"`. Determines the operational mode of the bot.
*   **`kiwoom`** (Required for `"live"` mode only): `Object`. Contains Kiwoom API credentials.
    *   `user_id`: `String`. Your Kiwoom account ID.
    *   `user_pw`: `String`. Your Kiwoom login password.
    *   `cert_pw`: `String`. Your digital certificate password for Kiwoom.
    *   `account_no`: `String`. Your brokerage account number (e.g., "1234567890").
*   **`ai_model`**: `Object`. Configuration for the AI prediction service.
    *   `endpoint_url`: `String`. URL of your AI prediction service.
    *   `api_key`: `String`. API key or token for authenticating with the AI service.
*   **`symbols`**: `Array of Strings`. List of ticker symbols the bot will trade (e.g., `["AAPL", "MSFT"]`).
*   **`time_zone`**: `String`. The primary market timezone the bot operates in (e.g., `"America/New_York"` for NYSE/NASDAQ, `"Asia/Seoul"` for KOSPI/KOSDAQ).

### Risk & Strategy Parameters

*   `initial_capital`: `Float`. The starting cash amount for trading (e.g., `10000.0`).
*   `max_position_pct`: `Float`. Maximum fraction of total capital to allocate to a single trade (e.g., `0.1` for 10%).
*   `atr_stop_multiplier`: `Float`. Multiplier for Average True Range (ATR) to set stop-loss levels (e.g., `1.0`).
*   `atr_take_multiplier`: `Float`. Multiplier for ATR to set take-profit levels (e.g., `2.0`).
*   `target_daily_return_pct`: `Float`. Daily profit target as a percentage of starting daily capital. If reached, the bot may stop opening new positions (e.g., `2.0` for 2%).
*   `stop_loss_pct`, `take_profit_pct`: `Float`. Fallback stop-loss and take-profit percentages (of entry price) if ATR is not available or not used (e.g., `1.0` for 1% stop-loss, `1.5` for 1.5% take-profit).
*   `daily_max_loss_pct`: `Float`. Maximum allowable drawdown per day as a percentage of starting daily capital. If reached, the bot may stop all trading activity for the day (e.g., `3.0` for 3%).

### Indicator Settings

*   `ema_short_period`, `ema_long_period`: `Integer`. Periods for short-term and long-term Exponential Moving Averages (e.g., `5`, `10`).
*   `rsi_period`, `rsi_oversold`, `rsi_overbought`: `Integer`. Period for Relative Strength Index (RSI) and its oversold/overbought thresholds (e.g., `14`, `30`, `70`).
*   `bb_period`, `bb_std_dev`: `Integer`, `Float`. Period and standard deviation multiplier for Bollinger Bands (e.g., `20`, `2.0`).
*   `atr_period`: `Integer`. Period for Average True Range (ATR) calculation (e.g., `14`).

### Backtest & Operational Settings

*   `historical_lookback_days`: `Integer`. Number of past days of 1-minute historical data to load at startup (e.g., `30`).
*   `loop_interval_sec`: `Float`. (Primarily for backtest mode) The polling interval in seconds for the main loop to check for signals and simulate time progression (e.g., `5.0`). In live mode, events are often tick-driven.
*   `broker_rate_limit_sec`: `Float`. Minimum delay in seconds between consecutive Kiwoom API calls to avoid exceeding rate limits (e.g., `0.2` for 5 calls/sec).

### Logging

*   `log_level`: `String`. Python's standard logging level (e.g., `"INFO"`, `"DEBUG"`, `"WARNING"`).
*   `log_file`: `String`. Path to the log file where bot activity will be recorded (e.g., `"logs/bot.log"`). Ensure the `logs/` directory exists.

## 3. Backtest Mode: Step-by-Step

Follow these instructions when `mode` in `config.json` is set to `"backtest"`.

### 3.1. Prepare Historical Data

1.  **Obtain Data**: Acquire 1-minute OHLCV (Open, High, Low, Close, Volume) data for each symbol specified in `config.json`.
2.  **CSV Format**: Save the data in CSV format. Each file should be named `{SYMBOL}_1min.csv` (e.g., `AAPL_1min.csv`) and placed in the `data/historical/` directory.
    *   **Required Columns**: `datetime`, `open`, `high`, `low`, `close`, `volume`.
    *   **Timestamp Format**: The `datetime` column should contain timestamps. These can be:
        *   Timezone-aware strings in the market's `time_zone` (specified in `config.json`).
        *   Naive datetime strings, which the bot will attempt to localize to the configured `time_zone`. (ISO 8601 format like `YYYY-MM-DD HH:MM:SS` is recommended).
3.  **Generate Sample Data (Optional)**: If you don't have historical data, you can generate a sample CSV using the provided script:
    ```bash
    python scripts/generate_sample_csv.py AAPL 2025-06-01 09:30 100
    ```
    This command creates `data/historical/AAPL_1min_sample.csv` with 100 minutes of synthetic data for AAPL, starting at 9:30 AM on June 1, 2025 (assuming `time_zone` is appropriate, e.g., NY time).

### 3.2. Run Backtest

1.  **Configure**: Ensure `mode` in `config.json` is set to `"backtest"`. Verify that the `symbols` list matches the base names of your CSV files (e.g., for `AAPL_1min.csv`, the symbol is `"AAPL"`).
2.  **Activate Environment**: If not already active, activate your Python virtual environment.
3.  **Execute Bot**:
    ```bash
    python -m src.trading_bot
    ```

### Backtest Process

*   **Initialization**: The bot loads `config.json`, instantiates `DataHandler` (which loads historical CSVs and computes initial indicators), `RiskManager`, and `AIClient`.
*   **Dummy Tick Feed**: A background thread starts, simulating a real-time tick feed. It generates a synthetic tick for each symbol at regular intervals (simulating seconds passing).
*   **Bar Finalization**: As simulated time progresses, these ticks are aggregated into 1-minute bars. When a new minute bar is "closed" (finalized), `DataHandler` updates its internal `historical_data` and recomputes all technical indicators for that symbol.
*   **Main Loop**: The main backtest loop runs at intervals defined by `loop_interval_sec`. In each iteration:
    *   For each symbol, `TradingBot.generate_signals()` is called using the latest available (simulated) market data.
    *   If a "BUY" or "SELL" signal is generated, `TradingBot.execute_order()` is called, which updates `RiskManager` by simulating the trade (no real orders are placed).
    *   `RiskManager.check_daily_targets()` is evaluated. If the daily profit target is met or the maximum daily drawdown is breached, the loop may terminate early.
    *   The bot checks if the simulated market closing time (`utils.is_nyse_close()`) has been reached. If so, the loop terminates.
*   **Final Cleanup**: After the main loop ends, `TradingBot._final_cleanup()` is called to simulate the liquidation of any open positions at the last known prices.
*   **Review Results**:
    *   Check the console output and the log file (`logs/bot.log` or as configured) for trade activity and summary statistics.
    *   `RiskManager.trade_history` (accessible if you modify the code to print or save it) will contain a list of all simulated trades, including entry/exit times and prices, P&L, and equity after each trade. This data can be used to calculate performance metrics like Sharpe ratio, win rate, and equity curve.

## 4. Live Mode: Step-by-Step

Follow these instructions when `mode` in `config.json` is set to `"live"`. **This mode requires a Windows operating system and a properly configured Kiwoom OpenAPI+ environment.**

### 4.1. Verify Kiwoom Setup (Windows Only)

1.  **Kiwoom HTS Running**: Ensure the Kiwoom HTS (trading program) is running and you are logged in with your credentials and digital certificate.
2.  **OpenAPI+ Enabled**: Confirm that OpenAPI+ is enabled and accessible.
3.  **`pykiwoom` Test**: (As mentioned in Prerequisites) Perform a basic connection test with `pykiwoom` to ensure your Python environment can communicate with the Kiwoom API.
    ```python
    # Example test snippet (run in Python REPL or script)
    from pykiwoom.kiwoom import Kiwoom
    try:
        kiwoom = Kiwoom()
        kiwoom.CommConnect(block=True) # Blocks until connection result is received
        if kiwoom.GetConnectState() == 1:
            print("Kiwoom OpenAPI+ Connected Successfully.")
        else:
            print("Kiwoom OpenAPI+ Connection Failed.")
    except Exception as e:
        print(f"Error connecting to Kiwoom: {e}")
    ```

### 4.2. Configure `config.json` for Live Trading

1.  **Set Mode**: Change `"mode"` to `"live"`.
2.  **Kiwoom Credentials**: Under the `kiwoom` block, accurately fill in your:
    *   `user_id`
    *   `user_pw`
    *   `cert_pw`
    *   `account_no` (ensure this is the correct account for trading).
3.  **Review Parameters**: Double-check all `symbols`, `time_zone`, and especially **risk parameters** (`initial_capital`, `max_position_pct`, `daily_max_loss_pct`, etc.) to ensure they are appropriate for live trading. **Start with small capital and conservative risk settings.**

### 4.3. Run in Live Mode

1.  **Activate Environment**: Activate your Python virtual environment.
2.  **Launch Bot**:
    ```bash
    python -m src.trading_bot
    ```

### Live Trading Process

*   **Initialization**: The bot loads `config.json`. `DataHandler` connects to the Kiwoom API, fetches initial historical data (using TR calls like `opt10080`), and computes indicators. `TradingBot` registers the `_on_receive_real_data` callback with the Kiwoom event system.
*   **Event-Driven Loop**: Unlike backtesting's fixed interval loop, live trading is largely event-driven.
    *   The main script thread enters a loop, primarily checking for market close conditions (`utils.is_nyse_close()`) or external stop signals (e.g., `Ctrl+C`).
    *   **Real-time Ticks**: The Kiwoom API pushes real-time market data (e.g., "주식체결" - stock execution) to the `TradingBot._on_receive_real_data` callback.
    *   This callback forwards the tick to `DataHandler.update_realtime()`.
    *   When enough ticks have arrived to finalize a new 1-minute bar, `DataHandler` does so and recomputes indicators.
    *   If a new bar is finalized, `TradingBot.generate_signals()` is called for the relevant symbol.
    *   If a "BUY" or "SELL" signal is generated, `TradingBot.execute_order()` calls `BrokerAPI.send_order()`, which sends the actual trade order to Kiwoom. `RiskManager` is updated with the live position details.
    *   `RiskManager` rules (daily P&L target, max drawdown) are continuously monitored.
*   **Final Cleanup (Market Close or Interruption)**:
    *   When the market closes (or if the bot is manually stopped with `Ctrl+C`), `TradingBot._final_cleanup()` is triggered.
    *   This method attempts to liquidate any open positions by sending `SELL` orders via `BrokerAPI` at the last known prices (or market orders if implemented).
*   **Monitoring & Logs**:
    *   Continuously monitor the log file specified in `config.json` (e.g., `logs/bot.log`) for all activities, including connections, data updates, signal generation, order submissions, and any errors.
    *   It is highly recommended to also monitor your positions and account activity directly through the Kiwoom HTS.

## 5. Common Workflow Commands

| Task                                       | Command                                                                 |
|--------------------------------------------|-------------------------------------------------------------------------|
| Activate virtual environment               | `source venv/bin/activate` (macOS/Linux) <br> `venv\Scripts\activate` (Windows) |
| Install/Update dependencies                | `pip install -r requirements.txt`                                       |
| Generate sample CSV for backtesting        | `python scripts/generate_sample_csv.py AAPL 2025-06-01 09:30 100`       |
| Run bot in Backtest Mode                   | `python -m src.trading_bot` (ensure `mode = "backtest"` in `config.json`) |
| Run bot in Live Mode (Windows, Kiwoom HTS active) | `python -m src.trading_bot` (ensure `mode = "live"` in `config.json`)   |
| Run automated tests                        | `pytest tests/`                                                         |

## 6. Tips & Troubleshooting

*   **CSV Loading Errors (Backtest)**:
    *   Ensure CSV filenames are *exactly* `{SYMBOL}_1min.csv` (e.g., `AAPL_1min.csv`, not `aapl_1min.csv` if your code is case-sensitive for symbols).
    *   Verify all required columns (`datetime`, `open`, `high`, `low`, `close`, `volume`) are present.
    *   Check timestamp format in CSVs. They should be parsable and ideally align with the `time_zone` in `config.json`.
*   **Kiwoom Connection Issues (Live Mode)**:
    *   Confirm the Kiwoom HTS program is running and you are successfully logged in.
    *   Ensure OpenAPI+ service is enabled within HTS settings.
    *   If using `pykiwoom`, ensure it's installed in the correct virtual environment and that your Python script's architecture (32-bit/64-bit) matches Kiwoom's (typically 32-bit).
    *   Check firewall settings that might be blocking communication.
*   **AI Endpoint Failures**:
    *   If `AIClient.predict` consistently returns `0.0` or logs errors:
        *   Verify `endpoint_url` and `api_key` in `config.json` are correct.
        *   Test network connectivity to the endpoint from the machine running the bot. Check for SSL certificate issues.
        *   Inspect bot logs for HTTP error codes (e.g., 401 Unauthorized, 403 Forbidden, 429 Too Many Requests, 500 Internal Server Error) and adjust `config.json` retry/timeout settings if applicable, or debug the AI service.
*   **Order Rejections or Failures (Live Mode)**:
    *   Check `logs/bot.log` for any error messages returned by the Kiwoom API after an order submission.
    *   Ensure your account has sufficient funds, correct trading permissions for the symbols, and that order parameters (price, quantity) are valid for the given market conditions.
*   **Rate Limit Warnings (Live Mode)**:
    *   Kiwoom imposes limits on API calls (e.g., TR requests per second, orders per second). If you see warnings or errors related to rate limits, try increasing `broker_rate_limit_sec` in `config.json` to add more delay between calls.
*   **Bot Stops Unexpectedly (Backtest)**:
    *   If the backtest finishes much earlier than expected (before the end of the historical data period), it might be due to risk limits defined in `config.json`.
    *   Check `target_daily_return_pct` and `daily_max_loss_pct`. If these are too restrictive for the test data, the bot will stop trading once a limit is hit. Try increasing these values for debugging purposes.
*   **Logs & Debugging**:
    *   For more detailed insight, set `log_level` in `config.json` to `"DEBUG"`.
    *   The primary source of information for troubleshooting is the log file (e.g., `logs/bot.log`). Look for error messages, stack traces, and warnings.

## 7. Advanced Usage & Customization

While this guide focuses on standard operation, the bot is designed for extensibility.

### Custom Plugins
You can inject custom logic at specific points in the trading process (before or after signal generation) using plugins.
1.  Create a Python file (e.g., `my_custom_plugins.py`).
2.  Define functions with a specific signature, for example: `def my_after_signal_logger(symbol: str, signal_data: dict): print(f"Signal for {symbol}: {signal_data}")`
3.  In your main script (before `bot.run()`), register your plugin:
    ```python
    from my_custom_plugins import my_after_signal_logger
    # Assuming 'bot' is your TradingBot instance
    bot.register_plugin("after_signal", my_after_signal_logger)
    ```
    For more details on plugin capabilities, refer to the `TradingBot.register_plugin` method and `generate_signals` implementation in `src/trading_bot.py` or `docs/architecture.md`.

### Alternative Data Sources or Brokers
Modifying the bot to use different data sources or broker APIs would involve more significant changes, likely requiring custom implementations of `DataHandler` or `BrokerAPI` components. Refer to `docs/architecture.md` for understanding how these components interact.

### Dockerization (for Backtesting)
For reproducible backtesting environments, you can containerize the application using Docker:
1.  Write a `Dockerfile` (e.g., based on a `python:3.9-slim` image).
2.  In the `Dockerfile`, copy project files and install dependencies from `requirements.txt`.
3.  Set the `ENTRYPOINT` or `CMD` to run the bot (e.g., `python -m src.trading_bot`).
4.  Build and run the Docker image:
    ```bash
    docker build -t trading-bot-backtest .
    # Ensure config.json is set for backtest and data is accessible (e.g., via volume mount)
    docker run --rm -v $(pwd)/data:/app/data -v $(pwd)/config.json:/app/config.json trading-bot-backtest
    ```
    Note: Live trading with Kiwoom is generally not suitable for Docker due to its Windows-specific dependencies and HTS GUI requirements.

---
End of Usage Guide. For a deeper understanding of the bot's internal structure and development guidelines, please see `docs/architecture.md` and the project `README.md`.