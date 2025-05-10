# metrics.py

from typing import Dict, Optional, List, Tuple
import numpy as np

def calculate_spread(best_bid: float, best_ask: float) -> Optional[float]:
    """Calculates the bid-ask spread."""
    if best_bid > 0 and best_ask > 0 and best_ask > best_bid:
        return best_ask - best_bid
    return None

def calculate_mid_price(best_bid: float, best_ask: float) -> Optional[float]:
    """Calculates the mid-price."""
    if best_bid > 0 and best_ask > 0 and best_ask > best_bid:
        return (best_ask + best_bid) / 2.0
    return None

def calculate_order_book_imbalance(bid_volume: float, ask_volume: float) -> Optional[float]:
    """Calculates the order book imbalance between best bid and ask volumes."""
    total_volume = bid_volume + ask_volume
    if total_volume > 0:
        return (bid_volume - ask_volume) / total_volume
    return None


def calculate_vwap(
    trades: List[Dict[str, any]], window_size_trades: int = 100
) -> Optional[float]:
    """Calculates Volume Weighted Average Price for the last N trades."""
    if not trades or window_size_trades <= 0:
        return None

    relevant_trades = trades[-window_size_trades:]
    total_value = sum(float(trade['p']) * float(trade['q']) for trade in relevant_trades)
    total_volume = sum(float(trade['q']) for trade in relevant_trades)

    if total_volume == 0:
        return None
    return total_value / total_volume


def calculate_trade_volume_per_second(
    trades: List[Dict[str, any]],
    current_time_ns: int,
    window_seconds: int = 1
) -> float:
    """Calculates the total trade volume within the last `window_seconds`."""
    if not trades or window_seconds <= 0:
        return 0.0

    window_ns = window_seconds * 1_000_000_000
    cutoff_time_ns = current_time_ns - window_ns

    volume = 0.0
    # Iterate backwards through trades as they are likely time-sorted (newest last)
    for trade in reversed(trades):
        trade_time_ms = trade["T"] # Binance trade timestamp is in milliseconds
        trade_time_ns = trade_time_ms * 1_000_000
        if trade_time_ns >= cutoff_time_ns:
            volume += float(trade['q'])
        else:
            # Trades are sorted by time, so we can stop early
            break
    return volume


# Example usage (for testing, not direct run):
if __name__ == "__main__":
    # --- Example Usage / Basic Tests ---
    # Mock data for testing
    mock_book_ticker_data = {
        'b': "100.00",  # best bid price
        'B': "10.0",    # best bid qty
        'a': "100.10",  # best ask price
        'A': "5.0"      # best ask qty
    }

    best_bid = float(mock_book_ticker_data['b'])
    best_ask = float(mock_book_ticker_data['a'])
    bid_qty = float(mock_book_ticker_data['B'])
    ask_qty = float(mock_book_ticker_data['A'])

    spread = calculate_spread(best_bid, best_ask)
    mid_price = calculate_mid_price(best_bid, best_ask)
    imbalance = calculate_order_book_imbalance(bid_qty, ask_qty)

    print(f"Spread: {spread}")
    print(f"Mid Price: {mid_price}")
    print(f"Imbalance: {imbalance}")

    # Mock trades for VWAP and volume/sec
    # Timestamps are simplified for this example
    # 'T' is Binance event time in ms
    # Let's assume current_time_ns is relative to the start of these trades + some offset
    current_time_s = time.time()
    current_time_ns_test = int(current_time_s * 1_000_000_000)

    mock_trades_list = [
        {'p': '99.90', 'q': '1.0', 'T': int(current_time_s - 2.5) * 1000}, # 2.5s ago
        {'p': '99.95', 'q': '0.5', 'T': int(current_time_s - 1.8) * 1000}, # 1.8s ago
        {'p': '100.00', 'q': '2.0', 'T': int(current_time_s - 0.9) * 1000}, # 0.9s ago
        {'p': '100.05', 'q': '1.5', 'T': int(current_time_s - 0.3) * 1000}  # 0.3s ago
    ]

    vwap = calculate_vwap(mock_trades_list, window_size_trades=3)
    print(f"VWAP (last 3 trades): {vwap}")

    volume_last_sec = calculate_trade_volume_per_second(
        mock_trades_list, current_time_ns_test, window_seconds=1
    )
    print(f"Volume (last 1 sec): {volume_last_sec}") # Expected: 2.0 + 1.5 = 3.5

    volume_last_2_sec = calculate_trade_volume_per_second(
        mock_trades_list, current_time_ns_test, window_seconds=2
    )
    # Expected: 2.0 + 1.5 + 0.5 = 4.0 (if times align)
    print(f"Volume (last 2 sec): {volume_last_2_sec}") 