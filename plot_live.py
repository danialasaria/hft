# plot_live.py

import asyncio
import time
import argparse
from collections import deque
from typing import Deque, List, Dict, Any, Optional

import matplotlib
matplotlib.use('macosx') # Use macOS native backend
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.ticker import ScalarFormatter
import numpy as np
import pandas as pd # For Parquet saving, if implemented

# Assuming feed.py and metrics.py are in the same directory or accessible via PYTHONPATH
from feed import binance_websocket_client
from metrics import (
    calculate_spread,
    calculate_mid_price,
    calculate_order_book_imbalance,
    calculate_vwap,
    calculate_trade_volume_per_second,
)

# Configuration
MAX_DATAPOINTS = 200  # Number of data points to display on the plots
PLOT_UPDATE_INTERVAL_MS = 200  # How often to redraw the plot

# Global data structures to be updated by WebSocket callbacks
# We use deques for efficient appends and pops from both ends
timestamps: Deque[float] = deque(maxlen=MAX_DATAPOINTS)
mid_prices: Deque[float] = deque(maxlen=MAX_DATAPOINTS)
spreads: Deque[float] = deque(maxlen=MAX_DATAPOINTS)
imbalances: Deque[float] = deque(maxlen=MAX_DATAPOINTS)
vwaps: Deque[float] = deque(maxlen=MAX_DATAPOINTS) # VWAP from trades
trade_volumes_per_sec: Deque[float] = deque(maxlen=MAX_DATAPOINTS)
last_trade_prices: Deque[float] = deque(maxlen=MAX_DATAPOINTS) # To plot recent trades on price chart

# Store all trades and book_tickers for metric calculation and potential saving
all_trades: Deque[Dict[str, Any]] = deque(maxlen=5000) # For VWAP and volume calculation

# --- Matplotlib Setup ---
fig, axs = plt.subplots(4, 1, figsize=(12, 10), sharex=True)
fig.suptitle("Real-time Crypto Microstructure Metrics")

# Subplot 1: Mid Price and Last Trade Price
axs[0].set_ylabel("Price (USD)")
(line_mid_price,) = axs[0].plot([], [], "r-", label="Mid Price")
(line_last_trade,) = axs[0].plot([], [], "ko", markersize=2, label="Last Trade")
axs[0].legend(loc="upper left")
axs[0].grid(True)
y_formatter = ScalarFormatter(useOffset=False, useMathText=False)
y_formatter.set_scientific(False)
axs[0].yaxis.set_major_formatter(y_formatter)

# Subplot 2: Spread
axs[1].set_ylabel("Spread (USD)")
(line_spread,) = axs[1].plot([], [], "g-", label="Bid-Ask Spread")
axs[1].legend(loc="upper left")
axs[1].grid(True)

# Subplot 3: Order Book Imbalance
axs[2].set_ylabel("Imbalance")
(line_imbalance,) = axs[2].plot([], [], "b-", label="Order Book Imbalance")
axs[2].axhline(0, color="gray", linestyle="--", linewidth=0.8)
axs[2].legend(loc="upper left")
axs[2].grid(True)

# Subplot 4: VWAP and Trade Volume per Second
axs[3].set_ylabel("VWAP (USD)", color="purple")
(line_vwap,) = axs[3].plot([], [], "p-", label="VWAP (100 trades)")
axs[3].tick_params(axis="y", labelcolor="purple")
axs[3].legend(loc="upper left")
axs[3].grid(True)

ax_volume = axs[3].twinx() # Share x-axis with VWAP
ax_volume.set_ylabel("Volume / sec", color="orange")
(line_volume_per_sec,) = ax_volume.plot([], [], "o-", color="orange", label="Trade Volume/sec")
ax_volume.tick_params(axis="y", labelcolor="orange")
ax_volume.legend(loc="upper right")

plt.xlabel("Time")
plt.tight_layout(rect=[0, 0, 1, 0.96]) # Adjust layout to make space for suptitle

# --- Data Processing and Plotting ---

async def data_collector_book_ticker(symbol: str):
    """Collects book ticker data and updates relevant metrics."""
    global last_trade_prices # only updated by trade stream, but plotted with book data time

    async for msg in binance_websocket_client(symbol, "bookTicker"):
        # msg fields: u (updateId), s (symbol), b (best bid), B (best bid qty), a (best ask), A (best ask qty)
        # _ts_received_ws, _ts_before_parse, _ts_after_parse
        
        # Save raw message (snapshotting) - Hint: Snapshot every raw WS frame to Parquet
        # For simplicity, this is not implemented here but would involve:
        # df = pd.DataFrame([msg])
        # df.to_parquet(f"{symbol}_bookTicker_{msg['u']}.parquet")

        current_time_sec = msg["_ts_received_ws"] / 1_000_000_000.0

        best_bid = float(msg['b'])
        best_bid_qty = float(msg['B'])
        best_ask = float(msg['a'])
        best_ask_qty = float(msg['A'])

        mid = calculate_mid_price(best_bid, best_ask)
        spread = calculate_spread(best_bid, best_ask)
        imbalance = calculate_order_book_imbalance(best_bid_qty, best_ask_qty)
        
        timestamps.append(current_time_sec)
        mid_prices.append(mid if mid is not None else np.nan)
        spreads.append(spread if spread is not None else np.nan)
        imbalances.append(imbalance if imbalance is not None else np.nan)
        
        # Append last known VWAP and Volume, or NaN if not yet calculated
        vwaps.append(vwaps[-1] if vwaps else np.nan)
        trade_volumes_per_sec.append(trade_volumes_per_sec[-1] if trade_volumes_per_sec else np.nan)
        last_trade_prices.append(np.nan)


async def data_collector_trades(symbol: str):
    """Collects trade data and updates relevant metrics."""
    global last_trade_prices # make sure this global is being assigned to

    async for msg in binance_websocket_client(symbol, "trade"):
        # msg fields: e (event type), E (event time), s (symbol), t (trade id), p (price), 
        # q (quantity), b (buyer order id), a (seller order id), T (trade time), 
        # m (is buyer market maker?), M (ignore)
        # _ts_received_ws, _ts_before_parse, _ts_after_parse

        # Save raw message
        # df = pd.DataFrame([msg])
        # df.to_parquet(f"{symbol}_trade_{msg['t']}.parquet")

        current_time_ns = msg["_ts_received_ws"]
        
        trade_price = float(msg['p'])

        all_trades.append(msg) # Add to global list of trades

        latest_vwap = calculate_vwap(list(all_trades), window_size_trades=100)
        latest_volume_per_sec = calculate_trade_volume_per_second(
            list(all_trades), current_time_ns, window_seconds=1
        )
        
        if vwaps: 
            vwaps[-1] = latest_vwap if latest_vwap is not None else np.nan
        if trade_volumes_per_sec:
            trade_volumes_per_sec[-1] = latest_volume_per_sec
        
        if last_trade_prices: # If the deque has been initialized by book_ticker
             last_trade_prices[-1] = trade_price # Update the last element with the current trade price


def update_plot(frame):
    """Updates the plot with new data."""
    if not timestamps:
        return []

    time_data = [pd.to_datetime(t, unit='s') for t in timestamps]

    # Ensure all data deques have the same length as timestamps for plotting consistency
    # This is a basic way to handle it; more sophisticated synchronization might be needed
    # if data sources update at very different rates and strict alignment is key.
    current_len = len(timestamps)
    
    def get_plot_data(dq: Deque) -> List:
        # If a deque is shorter, pad with last value or NaN. If longer, truncate.
        if not dq:
            return [np.nan] * current_len
        data = list(dq)
        if len(data) < current_len:
            data.extend([data[-1] if data else np.nan] * (current_len - len(data)))
        return data[:current_len]

    plot_mid_prices = get_plot_data(mid_prices)
    plot_last_trade_prices = get_plot_data(last_trade_prices)
    plot_spreads = get_plot_data(spreads)
    plot_imbalances = get_plot_data(imbalances)
    plot_vwaps = get_plot_data(vwaps)
    plot_trade_volumes_per_sec = get_plot_data(trade_volumes_per_sec)

    line_mid_price.set_data(time_data, plot_mid_prices)
    line_last_trade.set_data(time_data, plot_last_trade_prices)
    line_spread.set_data(time_data, plot_spreads)
    line_imbalance.set_data(time_data, plot_imbalances)
    line_vwap.set_data(time_data, plot_vwaps)
    line_volume_per_sec.set_data(time_data, plot_trade_volumes_per_sec)

    for ax_idx, ax in enumerate(axs):
        ax.relim()
        ax.autoscale_view()
        if ax_idx == 3 : # Special handling for the axis with a twin
            ax_volume.relim()
            ax_volume.autoscale_view()
    
    if time_data:
        # All subplots share the same x-axis due to sharex=True in plt.subplots()
        # We use axs[0] (if available) to set common x-axis limits.
        common_ax = axs[0] if len(axs) > 0 else fig.gca()
        start_time = time_data[0]
        end_time = time_data[-1]
        
        # Ensure start and end times are different to prevent plotting errors
        if start_time == end_time and len(time_data) > 1:
            # If all timestamps are identical somehow, create a small range
            # This can happen if MAX_DATAPOINTS is 1 or updates are too fast for float precision
            end_time = pd.to_datetime(timestamps[-1] + 0.1, unit='s') # Add a small offset
        elif start_time == end_time and len(time_data) == 1:
            # If only one data point, create a small window around it
            start_time = pd.to_datetime(timestamps[0] - 0.1, unit='s')
            end_time = pd.to_datetime(timestamps[0] + 0.1, unit='s')

        if start_time < end_time:
            common_ax.set_xlim(start_time, end_time)
            # Apply x-axis formatting (e.g., date format) to the bottom-most shared axis
            axs[-1].xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%H:%M:%S'))

    return [
        line_mid_price,
        line_last_trade,
        line_spread,
        line_imbalance,
        line_vwap,
        line_volume_per_sec,
    ]


async def main(symbol: str):
    print(f"Starting live plot for {symbol}...")
    print(f"Using {MAX_DATAPOINTS} data points, updating plot every {PLOT_UPDATE_INTERVAL_MS} ms.")

    task_book_ticker = asyncio.create_task(data_collector_book_ticker(symbol))
    task_trades = asyncio.create_task(data_collector_trades(symbol))

    ani = animation.FuncAnimation(
        fig, update_plot, interval=PLOT_UPDATE_INTERVAL_MS, blit=False, cache_frame_data=False
    )

    plt.show(block=False)

    try:
        while plt.fignum_exists(fig.number):
            await asyncio.sleep(0.05)  # Keep asyncio alive
            plt.pause(0.001)  # Allow MPL to process events
    except KeyboardInterrupt:
        print("Plotting interrupted.")
    finally:
        print("Shutting down data collectors...")
        task_book_ticker.cancel()
        task_trades.cancel()
        try:
            await asyncio.wait_for(task_book_ticker, timeout=1.0)
        except (asyncio.CancelledError, asyncio.TimeoutError):
            print("Book ticker collector did not shut down cleanly or was already done.")
        try:
            await asyncio.wait_for(task_trades, timeout=1.0)
        except (asyncio.CancelledError, asyncio.TimeoutError):
            print("Trades collector did not shut down cleanly or was already done.")
        plt.close(fig)
        print("Plot closed. Exiting.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Real-time crypto microstructure dashboard.")
    parser.add_argument(
        "symbol",
        type=str,
        default="btcusdt",
        nargs='?', # Makes the argument optional
        help="Crypto symbol to track (e.g., btcusdt). Defaults to btcusdt.",
    )
    args = parser.parse_args()

    try:
        asyncio.run(main(args.symbol))
    except KeyboardInterrupt:
        print("Program terminated by user.")
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc() 