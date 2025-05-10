# feed.py

import asyncio
import websockets
import orjson
import time
from typing import AsyncGenerator, Dict, Any

async def binance_websocket_client(
    symbol: str, stream_name: str
) -> AsyncGenerator[Dict[str, Any], None]:
    """Connects to a Binance WebSocket stream and yields messages."""
    uri = f"wss://data-stream.binance.vision/ws/{symbol.lower()}@{stream_name}"
    backoff_time = 1  # Initial backoff time in seconds

    while True:
        try:
            async with websockets.connect(uri) as websocket:
                print(f"Connected to {uri}")
                backoff_time = 1  # Reset backoff time on successful connection
                async for message in websocket:
                    ts_before_parse = time.monotonic_ns()
                    data = orjson.loads(message)
                    ts_after_parse = time.monotonic_ns()
                    data["_ts_before_parse"] = ts_before_parse
                    data["_ts_after_parse"] = ts_after_parse
                    data["_ts_received_ws"] = time.monotonic_ns()
                    yield data
        except (websockets.exceptions.ConnectionClosedError, websockets.exceptions.InvalidStatusCode) as e:
            print(f"Connection error: {e}. Reconnecting in {backoff_time} seconds...")
            await asyncio.sleep(backoff_time)
            backoff_time = min(backoff_time * 2, 60)  # Exponential backoff, capped at 60 seconds
        except Exception as e:
            print(f"An unexpected error occurred: {e}. Reconnecting in {backoff_time} seconds...")
            await asyncio.sleep(backoff_time)
            backoff_time = min(backoff_time * 2, 60)

async def main_trades(symbol: str):
    async for trade_data in binance_websocket_client(symbol, "trade"):
        # For latency_live.py: compute delta_us = now() - msg["T"]
        latency_ns = trade_data["_ts_received_ws"] - (trade_data["T"] * 1_000_000) # Binance 'T' is ms
        latency_us = latency_ns / 1000
        parse_latency_ns = trade_data["_ts_after_parse"] - trade_data["_ts_before_parse"]

        print(f"Symbol: {trade_data['s']}, Price: {trade_data['p']}, Qty: {trade_data['q']}, Trade Time: {trade_data['T']}, Latency: {latency_us:.2f} us, Parse Latency: {parse_latency_ns} ns")

async def main_book_ticker(symbol: str):
    async for book_data in binance_websocket_client(symbol, "bookTicker"):
        # 'u' is updateId, but using as proxy for event time if 'T' or 'E' not present
        # BookTicker does not have 'T' or 'E' (event time). 'u' is updateId, best we have.
        latency_ns = book_data["_ts_received_ws"] - (book_data["u"] * 1_000_000) 
        latency_us = latency_ns / 1000
        parse_latency_ns = book_data["_ts_after_parse"] - book_data["_ts_before_parse"]
        print(f"BookTicker: {book_data['s']}, Bid: {book_data['b']}, Ask: {book_data['a']}, Latency: {latency_us:.2f} us, Parse Latency: {parse_latency_ns} ns")

if __name__ == "__main__":
    async def run_main():
        print("feed.py is not meant to be run directly for the main application.")
        print("Use plot_live.py or latency_live.py instead.")
        # Example: To quickly test direct feed output for 'btcusdt@trade', uncomment below:
        # try:
        #     print("Starting test feed for btcusdt@trade...")
        #     async for msg in binance_websocket_client("btcusdt", "trade"):
        #         print(msg)
        # except KeyboardInterrupt:
        #     print("Test feed stopped.")

    try:
        asyncio.run(run_main())
    except KeyboardInterrupt:
        print("Manually interrupted.") 