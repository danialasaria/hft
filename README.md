# Crypto Microstructure Sandbox

A Python-based HFT research project that streams Binance spot-market data, reconstructs an in-memory limit-order-book, and surfaces real-time metrics plus a live latency dashboard.

![hftGif](https://github.com/user-attachments/assets/b1745aec-1c63-492c-a696-b47c2de76170)

## Project Structure

- `feed.py`: Async WebSocket client for Binance public data streams with reconnect logic.
- `orderbook.pyx`: Cython module for efficient in-memory order book reconstruction (price-level hash-map based).
- `metrics.py`: Calculates microstructure statistics (spread, imbalance, VWAP, per-second volume).
- `plot_live.py`: Real-time Matplotlib dashboard for price and volume metrics.
- `latency_live.py`: Real-time Matplotlib dashboard for WebSocket message latency.
- `tests/test_orderbook.py`: Property-based tests for `orderbook.pyx` using Hypothesis and Pytest.
- `requirements.txt`: Project dependencies.
- `README.md`: This file.

## Installation

1.  **Ensure you have Python >= 3.11 (developed and tested with 3.11.0) and a C++ compiler.**
    *   Using `pyenv` for managing Python versions is recommended, especially on macOS to ensure proper Tcl/Tk linkage for Matplotlib GUIs.
    *   On macOS, a C++ compiler can be installed with Xcode Command Line Tools: `xcode-select --install`
    *   On Linux (Debian/Ubuntu): `sudo apt-get update && sudo apt-get install build-essential python3-dev`
    *   On Windows, you'll need Microsoft C++ Build Tools (available with Visual Studio Installer).

2.  **Create and activate a virtual environment (recommended):**
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    (Note: The `orderbook.pyx` Cython module is compiled on-the-fly by `pyximport` when first used, e.g., by the test suite. Compilation artifacts are stored in the `.pyxbuild` directory.)

## Running the Dashboards

Make sure your virtual environment is activated.

*   **Live Metrics Dashboard:**
    ```bash
    python -m plot_live btcusdt
    ```
    (You can replace `btcusdt` with other Binance spot symbols, e.g., `ethusdt`)

*   **Live Latency Dashboard:**
    ```bash
    python -m latency_live btcusdt
    ```
    (Similarly, `btcusdt` can be replaced)

## Latency Measurement

### Method

The latency visualized in `latency_live.py` is calculated as the difference between the local monotonic timestamp when a trade message is received and processed by the `feed.py` client, and the server-side trade execution timestamp provided by Binance (`T` field in the trade message payload).

`delta_us = (local_monotonic_time_ns - binance_trade_time_ms * 1,000,000) / 1000`

Key timestamps:
*   `msg["T"]`: This is the original trade execution time in **milliseconds** since Unix epoch, as reported by Binance.
*   `_ts_received_ws`: This is a `time.monotonic_ns()` timestamp captured in `feed.py` immediately after a message is received from the `websockets` library and just before `orjson.loads()` is called. This aims to capture the end-to-end latency from Binance's matching engine to the Python user space process.
*   `_ts_before_parse` / `_ts_after_parse`: These `time.monotonic_ns()` timestamps are captured before and after `orjson.loads()` to measure JSON parsing cost, which is a component of the overall observed latency.

The rolling line plot shows this `delta_us` over time. The histogram shows the distribution of these deltas, typically binned in 1 millisecond increments.

### Expected Home Network Numbers

On a typical home internet connection (e.g., cable or fiber), latency to Binance servers (often located in Asia or co-located facilities) can vary significantly based on geographic location and network path.

*   **Ideal/Low Latency (e.g., <50ms):** Achievable if you are geographically close to Binance's WebSocket servers or have a very stable, low-hop connection. You might see a tight cluster in the histogram.
*   **Average Home Network (e.g., 50ms - 200ms):** This is a common range. You'll see a wider distribution in the histogram, potentially with some outliers due to network jitter.
*   **Higher Latency (e.g., >200ms):** Could be due to distant geographic location, less stable internet connection, or network congestion along the path.

The visualization helps in understanding the typical latency and its variance from your specific location. The recorded `_ts_before_parse` and `_ts_after_parse` also allow for splitting out the network latency component versus the local JSON parsing and processing latency within the Python application itself, though `latency_live.py` focuses on the end-to-end number using `_ts_received_ws` as the primary local timestamp.

## Running Tests

To run the property-based tests for the `orderbook.pyx` module:

1.  Ensure your virtual environment is activated and development dependencies (`pytest`, `hypothesis`) are installed (they are in `requirements.txt`).
2.  Navigate to the project root directory (the one containing `feed.py`, `orderbook.pyx`, etc.).
3.  Run Pytest:
    ```bash
    pytest
    ```
    Pytest will automatically discover and run the tests in the `tests/` directory. The `pyximport` setup within `tests/test_orderbook.py` will compile the `orderbook.pyx` module on-the-fly.
A `.pyxbuild` directory will be created to store compilation artifacts.

## Stretch Goals / Future Enhancements

*   Use Binance diff-depth stream (`@depth@100ms`) for finer-grained LOB updates beyond top-of-book.
*   Snapshot every raw WebSocket frame to Parquet files; build a replay mechanism for offline analysis and backtesting (especially for latency debugging).
*   Record monotonic timestamps *before* `orjson.loads` and *after* to split network vs. parse cost more explicitly in reporting (partially done in `feed.py` logging, could be surfaced in visuals).
*   Prefer functional style: continue to emphasize pure functions that transform immutable dicts/data structures where possible.
*   Add `mypy --strict` checks to CI/CD pipeline; fail build on any type error.
*   **Export latency statistics (e.g., mean, percentiles, histogram data) to Grafana via a Prometheus exporter.**
*   Implement more sophisticated order book features in `orderbook.pyx` (e.g., handling different update types from diff depth stream, order queue tracking if possible from data).
*   Expand `metrics.py` with more advanced microstructure indicators (e.g., Volatility, Order Flow Imbalance variants, Depth-weighted prices).
*   Containerize the application using Docker for easier deployment and environment consistency. 
