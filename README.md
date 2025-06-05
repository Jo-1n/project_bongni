# Trading Bot Repository

This project implements a modular, AI‐optimized trading bot that can operate in both backtest and live modes using the Kiwoom OpenAPI (on Windows).

## Key Features

*   **Modular Architecture**: Clear separation of concerns for easier maintenance and extension (see `docs/architecture.md`).
*   **AI Integration**: Augments technical signals with an external AI endpoint for improved decision-making.
*   **Backtest & Live Modes**: Supports both historical data simulation and real-time trading with Kiwoom.
*   **Risk Management**: Implements volatility-adjusted position sizing (ATR-based), dynamic Stop-Loss/Take-Profit, and daily P&L limits.
*   **Plugin System**: Allows for injecting custom logic via hooks without modifying core code.
*   **Test Coverage**: Includes unit and integration tests to ensure reliability.

## Repository Structure

A brief overview of the main directories:
```
project_root/
├── config.json         # Main configuration file
├── requirements.txt    # Python dependencies
├── README.md           # This file
├── docs/               # Detailed documentation (Usage Guide, Architecture)
├── data/               # Historical data for backtesting
├── src/                # Source code for the bot
└── tests/              # Unit and integration tests
```
For a detailed explanation of each component, please refer to the [Architecture Overview](docs/architecture.md).

## Prerequisites

*   Python 3.9+
*   Git
*   (For Live Mode) Windows operating system & Kiwoom OpenAPI+ installed.
*   (Optional) An AI Model Endpoint and API key if using AI-driven predictions.

For detailed setup instructions, please see the [Prerequisites section in the Usage Guide](docs/Usage.md#1-prerequisites).

## Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/yourusername/trading-bot.git
    cd trading-bot
    ```
2.  **Create a virtual environment and install dependencies:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On macOS/Linux
    # venv\Scripts\activate   # On Windows
    pip install --upgrade pip
    pip install -r requirements.txt
    ```
Detailed installation steps are available in the [Usage Guide](docs/Usage.md#1-prerequisites).

## Configuration

The bot's behavior is controlled by `config.json` located in the project root. You will need to:
1.  Copy `config.example.json` to `config.json` (if an example file is provided).
2.  Edit `config.json` to set your API keys, trading symbols, risk parameters, and other settings.

A comprehensive explanation of all configuration options can be found in the [Configuration section of the Usage Guide](docs/Usage.md#2-configuring-configjson).

## Usage

The bot can be run in either backtest or live mode.

*   **To run in Backtest Mode:**
    Ensure `mode` is set to `"backtest"` in `config.json` and you have historical data prepared.
    ```bash
    python -m src.trading_bot
    ```
*   **To run in Live Mode (Windows Only):**
    Ensure `mode` is set to `"live"` in `config.json` and Kiwoom OpenAPI is correctly set up.
    ```bash
    python -m src.trading_bot
    ```

For detailed step-by-step instructions on preparing data, running the bot in different modes, and monitoring its activity, please consult the **[Usage Guide](docs/Usage.md)**.

## Development & Testing

To run the automated tests:
```bash
pytest tests/
```
If you are interested in understanding the internal workings of the bot or contributing to its development, please review the [Architecture Overview](docs/architecture.md).

## Contributing

Contributions are welcome! Please fork the repository, create a feature branch, and submit a pull request.
Ensure your code adheres to PEP8 standards and includes tests for any new functionality.
(Consider creating a `CONTRIBUTING.md` file for more detailed guidelines.)

## Project Roadmap / Next Steps

*   Dockerize the backtest environment for enhanced reproducibility.
*   Add more comprehensive Windows-specific instructions for live deployment.
*   Enhance AI features: incorporate additional data sources (e.g., order book, macroeconomic signals).
*   Extend risk management: support alternative volatility measures or custom risk rules via plugins.
*   Implement notifications (e.g., Slack, email) for significant trading events or errors.