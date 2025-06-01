# latency_live.py

import asyncio
import time
import argparse
from collections import deque
from typing import Deque, List, Tuple

import matplotlib
matplotlib.use('macosx') # Use macOS native backend
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import matplotlib.ticker as ticker
import numpy as np
import pandas as pd # For x-axis datetime formatting

from feed import binance_websocket_client

# Configuration
MAX_DATAPOINTS = 200 # Number of data points for the rolling line plot
MAX_DELTAS = 5000  # Ring buffer size for latency deltas
PLOT_UPDATE_INTERVAL_MS = 200  # How often to redraw the plot
HIST_BINS = 100 # Number of bins for the histogram (e.g., 1ms bins up to 100ms)
HIST_RANGE_MS = (-500, 500) # Range of histogram in milliseconds - WIDENED FOR TESTING

# Global data structures
latency_deltas_us: Deque[float] = deque(maxlen=MAX_DELTAS)
wall_clock_times: Deque[float] = deque(maxlen=MAX_DATAPOINTS) # For the rolling line plot, subset of MAX_DELTAS
rolling_latency_plot_data: Deque[float] = deque(maxlen=MAX_DATAPOINTS) # Subset for plot

# --- Matplotlib Setup ---
fig, axs = plt.subplots(2, 1, figsize=(12, 8))
fig.suptitle("Real-time WebSocket Latency to Binance (Trades)")

# Subplot 1: Rolling line of delta_us vs. wall-clock time
axs[0].set_ylabel("Latency (µs)")
axs[0].set_xlabel("Wall Clock Time")
(line_latency_rolling,) = axs[0].plot([], [], "b-", label="Trade Latency (now - msg['T'])")
axs[0].legend(loc="upper left")
axs[0].grid(True)

# Subplot 2: Histogram of delta_us
axs[1].set_xlabel("Latency (ms)")
axs[1].set_ylabel("Frequency")
axs[1].grid(True)
# Histogram will be updated directly, no line object needed beforehand for histtype='step'

plt.tight_layout(rect=[0, 0, 1, 0.95])


async def latency_data_collector(symbol: str):
    """Collects trade data and calculates latency."""
    async for msg in binance_websocket_client(symbol, "trade"):
        # msg fields: T (trade time in ms), _ts_received_ws (monotonic ns when received)
        # msg["T"] is Binance millisecond trade timestamp
        # _ts_received_ws is monotonic time in nanoseconds when message was processed by our feed client
        
        binance_trade_time_ns = msg["T"] * 1_000_000  # Convert ms to ns
        local_receive_time_ns = msg["_ts_received_ws"]
        
        delta_ns = local_receive_time_ns - binance_trade_time_ns
        delta_us = delta_ns / 1000.0
        
        # --- DIAGNOSTIC PRINT FOR LATENCY CALC ---
        print(f"LatencyCalc | TradeTime(T): {msg['T']}ms | LocalRecv: {local_receive_time_ns}ns | BinanceTradeTime: {binance_trade_time_ns}ns | Delta: {delta_us:.2f}µs")
        # --- END DIAGNOSTIC PRINT ---

        latency_deltas_us.append(delta_us)
        
        # Use the _ts_received_ws as the basis for wall clock time for consistency
        wall_clock_times.append(local_receive_time_ns / 1_000_000_000.0) # Convert ns to seconds for datetime
        rolling_latency_plot_data.append(delta_us)

def update_latency_plot(frame):
    if not latency_deltas_us:
        return []

    # Subplot 1: Rolling Latency Line
    if wall_clock_times:
        plot_times = [pd.to_datetime(t, unit='s') for t in wall_clock_times]
        # Use rolling_latency_plot_data directly (it's already in µs)
        line_latency_rolling.set_data(plot_times, rolling_latency_plot_data)
        axs[0].relim()
        axs[0].autoscale_view()
        if plot_times:
            axs[0].set_xlim(plot_times[0], plot_times[-1])
            axs[0].xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%H:%M:%S.%f'))
            # fig.autofmt_xdate() # Can be heavy

    # Subplot 2: Histogram
    axs[1].clear() # Clear previous histogram
    # Convert latency_deltas_us (microseconds) to milliseconds for histogram
    latencies_ms = [d / 1000.0 for d in latency_deltas_us]
    axs[1].hist(latencies_ms, bins=HIST_BINS, range=HIST_RANGE_MS, histtype="step", color="green", label=f"Latency Distribution (last {len(latency_deltas_us)} msgs)")
    axs[1].set_xlabel("Latency (ms)")
    axs[1].set_ylabel("Frequency")
    axs[1].legend(loc="upper right")
    axs[1].grid(True)
    
    # Re-apply tight_layout if clearing and redrawing elements changed spacing much
    # fig.tight_layout(rect=[0, 0, 1, 0.95]) # Might be too slow if called every frame

    return [line_latency_rolling]


async def main(symbol: str):
    print(f"Starting live latency plot for {symbol} trades...")
    print(f"Ring buffer size: {MAX_DELTAS} deltas.")
    print(f"Plotting last {MAX_DATAPOINTS} for rolling line graph.")

    data_task = asyncio.create_task(latency_data_collector(symbol))

    ani = animation.FuncAnimation(
        fig, update_latency_plot, interval=PLOT_UPDATE_INTERVAL_MS, blit=False, cache_frame_data=False
    ) # blit=False because we are clearing and redrawing hist

    plt.show(block=False)

    try:
        while plt.fignum_exists(fig.number):
            await asyncio.sleep(0.05) # Keep asyncio alive
            plt.pause(0.001) # Allow MPL to process events
    except KeyboardInterrupt:
        print("Latency plotting interrupted.")
    finally:
        print("Shutting down latency data collector...")
        data_task.cancel()
        try:
            await asyncio.wait_for(data_task, timeout=1.0)
        except (asyncio.CancelledError, asyncio.TimeoutError):
            print("Latency data collector did not shut down cleanly or was already done.")
        plt.close(fig)
        print("Latency plot closed. Exiting.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Real-time WebSocket latency visualizer for Binance trades.")
    parser.add_argument(
        "symbol",
        type=str,
        default="btcusdt",
        nargs='?',
        help="Crypto symbol for trade stream (e.g., btcusdt). Defaults to btcusdt.",
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