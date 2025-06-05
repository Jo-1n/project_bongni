# Usage Guide

This document provides step-by-step instructions for installing, configuring, and running the **Automatic Trading Bot**. It also covers how to perform backtesting, adjust key parameters, and troubleshoot common issues.

---

## 1. Prerequisites

1.  **Operating System**
    *   Linux (Ubuntu 20.04 LTS or later recommended)
    *   macOS (Catalina or later)
    *   Windows 10/11 (with WSL2 or native Python 3.8+)

2.  **Python Version**
    *   **Python 3.8** or higher (tested up to 3.11).
    *   Ensure `python --version` or `python3 --version` returns `3.8.x` or above.

3.  **Git**
    *   Required to clone the repository.
    *   Check with `git --version`.

4.  **Kiwoom OpenAPI (for live trading)**
    *   Install Kiwoom HTS (OpenAPI+) on a Windows machine (if you plan to run the bot on Windows).
    *   Copy the `PyKiwoom` library (or any Kiwoom Python wrapper) into your virtual environment.
    *   Ensure your digital certificate (공인인증서) is registered in HTS.

5.  **AI Model Endpoint (optional)**
    *   If you plan to integrate real AI predictions, register for an AI provider (e.g., your own REST service or third-party endpoint).
    *   Obtain an API key or token.

6.  **Internet Connection**
    *   Required for:
        *   Real-time data (Kiwoom or alternative data feed).
        *   AI model REST API calls.
        *   (Optionally) package installation (`pip install`).

7.  **Virtual Environment (recommended)**
    *   Create a dedicated virtual environment to isolate dependencies:
        ```bash
        python3 -m venv venv
        source venv/bin/activate    # macOS/Linux
        venv\Scripts\activate       # Windows (cmd.exe or PowerShell)
        ```

---

## 2. Installation

1.  **Clone the Repository**
    Replace the URL below with your own repository’s URL:
    ```bash
    git clone https://github.com/Jo-1n/project_bongni.git
    cd project_bongni
    ```

2.  **Activate Virtual Environment**
    ```bash
    python3 -m venv venv
    source venv/bin/activate       # macOS/Linux
    venv\Scripts\activate          # Windows
    ```

3.  **Install Python Dependencies**
    ```bash
    pip install --upgrade pip
    pip install -r requirements.txt
    ```

4.  **Verify Directory Structure**
    ```text
    trading_bot_project/
    ├── README.md
    ├── requirements.txt
    ├── config.json
    ├── main.py
    ├── src/
    │   ├── config.py
    │   ├── data_handler.py
    │   ├── risk_manager.py
    │   ├── trading_bot.py
    │   └── utils.py
    ├── data/
    │   ├── historical/
    │   └── realtime/
    ├── logs/
    │   └── bot.log
    ├── docs/
    │   ├── architecture.md
    │   └── usage.md
    └── tests/
    ```
    *   If any directories (`logs/`, `data/historical/`, `data/realtime/`) are missing, create them manually:
        ```bash
        mkdir -p logs data/historical data/realtime
        ```

---

## 3. Configuration

1.  **Open `config.json`**
    Edit or overwrite the placeholder values in `config.json`. The file should be in the project root directory.
    ```json
    {
      // 1) Kiwoom OpenAPI Credentials
      "kiwoom": {
        "user_id": "YOUR_KIWOOM_ID",
        "user_pw": "YOUR_KIWOOM_PASSWORD",
        "cert_pw": "YOUR_KIWOOM_CERT_PASSWORD",
        "account_no": "1234567890123"
      },

      // 2) AI Model Endpoint & API Key
      "ai_model": {
        "endpoint_url": "https://api.your-ai-provider.com/predict",
        "api_key": "YOUR_AI_API_KEY"
      },

      // 3) Trading Symbols & Time Zone
      "symbols": ["AAPL", "MSFT", "GOOGL", "TSLA"],
      "time_zone": "America/New_York",

      // 4) Risk Management Parameters
      "initial_capital": 1000.0,
      "max_position_pct": 0.5,
      "target_daily_return_pct": 2.0,   // 2% daily target return
      "stop_loss_pct": 1.0,             // 1% stop-loss per position
      "take_profit_pct": 1.5,           // 1.5% take-profit per position
      "daily_max_loss_pct": 3.0,        // 3% daily drawdown limit

      // 5) Technical Indicator Settings
      "ema_short_period": 5,
      "ema_long_period": 10,
      "rsi_period": 14,
      "rsi_oversold": 30,
      "rsi_overbought": 70,
      "bb_period": 20,
      "bb_std_dev": 2,

      // 6) Data Collection / Backtesting Settings
      "historical_lookback_days": 30,
      "historical_bar_period": "1min",

      // 7) Order Retry & Loop Intervals
      "order_retry_interval_sec": 1.0,
      "loop_interval_sec": 5.0,

      // 8) Logging
      "log_level": "INFO",
      "log_file": "logs/bot.log"
    }
    ```
    *   **Important**: Remove any `//` comments before saving, as JSON does not support comments in production.
    *   Ensure that `ai_model.endpoint_url` and `ai_model.api_key` are correct if you intend to use real AI predictions.

2.  **(Optional) Use a `.env` File**
    To avoid storing sensitive credentials directly in `config.json`, you can create a `.env` file in the project root:
    ```env
    KIWOOM_ID=your_id_here
    KIWOOM_PW=your_password_here
    KIWOOM_CERT_PW=your_cert_password_here
    AI_API_KEY=your_ai_api_key_here
    ```
    Then, modify `main.py` to load environment variables first (using `python-dotenv`). In `src/config.py`, prefer `os.getenv("KIWOOM_ID")` if present.

---

## 4. Running the Bot (Live Trading)

1.  **Activate Virtual Environment (if not already active):**
    ```bash
    source venv/bin/activate     # macOS/Linux
    venv\Scripts\activate        # Windows
    ```

2.  **Ensure Kiwoom HTS and OpenAPI are Configured**
    *   The Kiwoom HTS client must be installed and properly registered with your digital certificate.
    *   Confirm you can log in and request historical data manually.

3.  **Start the Bot**
    ```bash
    python main.py
    ```
    *   The bot will log information to both the console and `logs/bot.log`.
    *   On startup:
        *   Historical data for all symbols will be loaded.
        *   Kiwoom login will be attempted (if implemented).
        *   A background thread will begin generating (dummy or real) tick data.
        *   The main loop will wait until the market is open, then start computing indicators and submitting orders.

4.  **Monitor Logs**
    *   Tail the log file in a separate terminal to watch real-time events:
        ```bash
        tail -f logs/bot.log
        ```
    *   Common log entries include:
        ```log
        2025-06-05 05:30:00 [INFO] [INIT] TradingBot initialized. Trading day: 2025-06-05
        2025-06-05 05:31:02 [INFO] [DATA] AAPL historical data loaded: 43200 rows
        2025-06-05 05:31:02 [INFO] [DATA] MSFT historical data loaded: 43200 rows
        2025-06-05 05:31:02 [INFO] [DATA] GOOGL historical data loaded: 43200 rows
        2025-06-05 05:31:02 [INFO] [DATA] TSLA historical data loaded: 43200 rows
        2025-06-05 05:31:02 [INFO] [BOT] Started real-time tick feed
        2025-06-05 06:00:00 [INFO] [BOT] Signal generated: AAPL → BUY (price: 128.45, qty: 3)
        2025-06-05 06:00:00 [INFO] [RISK] AAPL position opened: entry=128.45, qty=3, SL=127.16, TP=130.37
        2025-06-05 06:05:00 [INFO] [DATA] AAPL 1-minute bar added: 2025-06-05 06:05:00, close=128.12
        2025-06-05 06:05:00 [INFO] [BOT] Signal generated: AAPL → HOLD
        2025-06-05 06:10:00 [INFO] [DATA] AAPL 1-minute bar added: 2025-06-05 06:10:00, close=130.50
        2025-06-05 06:10:00 [INFO] [BOT] Signal generated: AAPL → SELL_TP (take-profit)
        2025-06-05 06:10:00 [INFO] [RISK] AAPL position closed: exit=130.50, P&L=6.15, capital=1006.15
        ```

5.  **Stop the Bot**
    *   Press `Ctrl+C` (SIGINT) in the terminal where `main.py` is running.
    *   The bot will catch the exception and run `_final_cleanup()` to close any remaining open positions.

---

## 5. Backtesting Mode

To simulate trades on historical data without sending real orders, follow these steps:

1.  **Populate `data/historical/`**
    *   For each symbol, place a CSV file named `{SYMBOL}_1min.csv`. Example:
        ```text
        data/historical/AAPL_202506.csv
        data/historical/MSFT_202506.csv
        ```
    *   CSV schema (columns):
        ```csv
        datetime,open,high,low,close,volume
        2025-05-01 09:30:00,126.83,127.15,126.50,126.85,1204320
        2025-05-01 09:31:00,126.85,127.00,126.60,126.90,980321
        ...
        ```
    *   Ensure the CSV uses ISO 8601 timestamps and is sorted ascending by time.

2.  **Modify `TradingBot` for Backtesting**
    *   Add a boolean flag `backtest_mode` to the `Config` or `TradingBot` constructor.
    *   In the `run()` method, replace the real-time tick pull and sleeping loop with a loop over each minute in the historical DataFrame:
        ```python
        for timestamp, bar in df_historical.iterrows():
            # Simulate tick stream by treating each bar as the “latest” minute
            self.data_handler.historical_data[symbol].loc[timestamp] = bar
            signal = self.generate_signals(symbol)
            if signal["signal"] != "HOLD":
                self.execute_order(signal, symbol)
            # Advance to next bar; no need to sleep
        ```
    *   Skip `fetch_realtime_ticks()` entirely in backtest mode.
    *   Disable actual API calls in `execute_order`; instead record trades to a results DataFrame.

3.  **Run Backtest**
    ```bash
    # Edit main.py or create a separate backtest script, e.g. backtest.py
    python backtest.py
    ```
    *   After completion, analyze results: cumulative P&L, Sharpe ratio, maximum drawdown, win rate.
    *   Optionally, save a CSV of trade logs:
        ```text
        trades/
          backtest_AAPL_202506.csv
          backtest_MSFT_202506.csv
        ```

---

## 6. Customizing Parameters

All essential parameters are controlled via `config.json`. Below are descriptions of each:

1.  **`kiwoom.user_id`, `kiwoom.user_pw`, `kiwoom.cert_pw`, `kiwoom.account_no`**
    *   Credentials for Kiwoom HTS/OpenAPI.
    *   If using environment variables, set `KIWOOM_ID`, `KIWOOM_PW`, `KIWOOM_CERT_PW`.

2.  **`ai_model.endpoint_url`, `ai_model.api_key`**
    *   REST API endpoint for AI predictions (if used).
    *   Must accept input JSON (e.g., recent features) and return a JSON with a numeric `predicted_return`.
    *   If not using AI, you may leave these empty and remove the AI prediction logic in `generate_signals`.

3.  **`symbols`**
    *   A list of uppercase ticker strings.
    *   The bot will trade each symbol in parallel.
    *   Example: `["AAPL", "MSFT", "GOOGL", "TSLA"]`.

4.  **`time_zone`**
    *   Time zone in which `trading_day` is determined.
    *   Use IANA format (e.g., `"America/New_York"` for NASDAQ times, or `"Asia/Seoul"` if you prefer Korean local time).

5.  **Risk Management Parameters (all percentages)**
    *   `initial_capital` (float): Starting account equity in USD.
    *   `max_position_pct` (float): Maximum fraction of equity to allocate per position (e.g., `0.5` = 50%).
    *   `target_daily_return_pct` (float): Daily return target as a whole percentage (e.g., `2.0` = 2%). If reached, no new positions are opened.
    *   `stop_loss_pct` (float): Per-position stop-loss percentage (e.g., `1.0` = 1%).
    *   `take_profit_pct` (float): Per-position take-profit percentage (e.g., `1.5` = 1.5%).
    *   `daily_max_loss_pct` (float): Maximum allowable drawdown per day (e.g., `3.0` = 3%). If reached, no new positions are opened.

6.  **Technical Indicator Settings**
    *   `ema_short_period` (int): Time window (minutes) for short EMA.
    *   `ema_long_period` (int): Time window (minutes) for long EMA.
    *   `rsi_period` (int): Lookback window for RSI.
    *   `rsi_oversold` (int): RSI threshold below which the symbol is considered oversold (e.g., `30`).
    *   `rsi_overbought` (int): RSI threshold above which the symbol is considered overbought (e.g., `70`).
    *   `bb_period` (int): Lookback window for Bollinger Bands.
    *   `bb_std_dev` (float): Standard deviation multiplier for Bollinger Bands.

7.  **Data Collection / Backtesting**
    *   `historical_lookback_days` (int): Number of days of historical bars (1-minute) to preload at startup.
    *   `historical_bar_period` (string): Timeframe for historical bars, e.g., `"1min"`.

8.  **Order Retry & Loop Intervals**
    *   `order_retry_interval_sec` (float): Seconds to wait before retrying a failed order.
    *   `loop_interval_sec` (float): Seconds to sleep between each iteration of the main loop when the market is open. Lower values → higher frequency but greater CPU usage.

9.  **Logging**
    *   `log_level` (string): Logging verbosity. Use `"DEBUG"`, `"INFO"`, `"WARNING"`, `"ERROR"`, or `"CRITICAL"`.
    *   `log_file` (string): Path to the log file. Typically `logs/bot.log`.

---

## 7. Troubleshooting & Common Issues

1.  **Bot Stops Immediately (No Error)**
    *   Likely because `risk_manager.check_daily_targets()` returned `False` at startup (e.g., capital was accidentally set too high or negative).
    *   Check the initial values of `initial_capital`, `target_daily_return_pct`, and `daily_max_loss_pct` in `config.json`.

2.  **No Historical Data Loaded**
    *   If you see `"[DATA] <SYMBOL> historical data loaded: 0 rows"`, verify that your data source is reachable.
    *   For dummy mode, random data is generated—ensure `historical_lookback_days > 0`.
    *   For real data, confirm Kiwoom OpenAPI TR calls are implemented in `fetch_historical()`.

3.  **No Signals Ever Generated**
    *   Indicators require a minimum number of rows:
        ```
        length ≥ max(ema_long_period, rsi_period, bb_period)
        ```
    *   If your historical dataset is too short or missing columns (`close`, `volume`), signals cannot be computed.
    *   Check `data_handler.compute_indicators()` and ensure DataFrame indices are proper datetime objects with minute frequency.

4.  **Kiwoom API Login Fails**
    *   Confirm that HTS is running, your credentials are correct, and your digital certificate is valid.
    *   If using Python on Linux/macOS, you need Windows + emulator (e.g., Wine) or a remote Windows VM because Kiwoom OpenAPI only runs on Windows.

5.  **Order Execution Errors**
    *   Verify that `execute_order()` replaces the `TODO` with actual calls to `self.kiwoom.send_order(...)` or your broker’s SDK.
    *   Check return codes from `send_order()` to ensure the order was submitted successfully; if not, retry after `order_retry_interval_sec`.

6.  **High CPU Usage During Backtesting**
    *   If backtesting over millions of bars, loop iteration overhead may be high.
    *   Consider vectorized backtesting frameworks (e.g., `backtrader`, `zipline`) for large-scale simulations, or batch indicator calculations instead of per-bar recalculation.

7.  **Incorrect Time Zone Conversions**
    *   `TradingBot.initialize()` uses a simplified UTC→`time_zone` conversion. For production, use:
        ```python
        import pytz
        from datetime import datetime # Ensure datetime is imported

        now_utc = datetime.utcnow().replace(tzinfo=pytz.utc)
        tz = pytz.timezone(self.config.time_zone)
        now_local = now_utc.astimezone(tz)
        ```
    *   Always verify that `trading_day` matches the exchange’s calendar (holidays, early closes).

---

## 8. Extending & Customizing

1.  **Adding New Indicators**
    *   Implement additional functions in `data_handler.compute_indicators()`:
        *   **MACD:**
            ```python
            # Assuming 'ta' is imported, e.g., import ta
            macd = ta.trend.MACD(close=df["close"])
            df["macd"] = macd.macd()
            df["macd_signal"] = macd.macd_signal()
            df["macd_hist"] = macd.macd_diff()
            ```
        *   **Stochastic Oscillator:**
            ```python
            # Assuming 'ta' is imported
            stoch = ta.momentum.StochasticOscillator(
                high=df["high"], low=df["low"], close=df["close"], window=14, smooth_window=3
            )
            df["stoch_k"] = stoch.stoch()
            df["stoch_d"] = stoch.stoch_signal()
            ```

2.  **Custom Signal Logic**
    *   Create a new module `src/strategies.py` that exports multiple strategy classes (e.g., `EMAStrategy`, `MeanReversionStrategy`, `RSIStrategy`).
    *   In `trading_bot.generate_signals()`, select the active strategy based on configuration.
    *   Example:
        ```python
        from src.strategies import EMAStrategy #, BulkSignalStrategy (if defined)

        # In generate_signals:
        # strategy = EMAStrategy(self.config, df)
        # return strategy.generate()
        ```

3.  **Multiple Brokers or Simultaneous Accounts**
    *   Extend `config.json` to include multiple broker endpoints and credentials.
    *   Instantiate separate `TradingBot` instances (each with its own `DataHandler` and `RiskManager`) per account or region.

4.  **Parallel Processing**
    *   For a large number of symbols, consider spawning multiple processes (via `multiprocessing`) or asynchronous tasks (via `asyncio`) so that indicator computation for each symbol does not block others.
    *   Example (pseudo-code):
        ```python
        import asyncio

        # async def process_symbol(symbol):
        #     while is_market_open(): # is_market_open() needs to be defined
        #         signal = generate_signals(symbol) # generate_signals() needs to be defined
        #         if signal["signal"] != "HOLD":
        #             await execute_order_async(signal, symbol) # execute_order_async() needs to be defined
        #         await asyncio.sleep(loop_interval_sec) # loop_interval_sec needs to be defined

        # async def main_loop():
        #     tasks = [asyncio.create_task(process_symbol(sym)) for sym in config.symbols] # config needs to be defined
        #     await asyncio.gather(*tasks)

        # asyncio.run(main_loop())
        ```

---

## 9. Summary

This Usage Guide has covered:

1.  **Prerequisites**: Required OS, Python version, Kiwoom HTS, AI model endpoint.
2.  **Installation**: Cloning, virtual environment, dependency installation, directory setup.
3.  **Configuration**: Detailed explanation of every key in `config.json`, environment variable precedence.
4.  **Running the Bot**: How to start live trading, how logs appear, how to stop safely.
5.  **Backtesting Mode**: Steps to simulate historical performance without real orders.
6.  **Customizing Parameters**: Explanation of each field in `config.json`.
7.  **Troubleshooting**: Common pitfalls and their remedies.
8.  **Extending & Customizing**: Suggestions for adding indicators, custom strategies, multi-broker support, and parallelization.

By following this guide and adjusting parameters in `config.json`, you can quickly deploy a working intraday trading bot, test strategies on historical data, and ensure robust risk management. Always exercise due care when moving from simulation to real-money trading: thoroughly backtest, monitor logs, and start with minimal capital allocations.

Happy trading!