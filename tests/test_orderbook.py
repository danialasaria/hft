# tests/test_orderbook.py

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
import pyximport
pyxtemp_folder = ".pyxbuild"
import os
if not os.path.exists(pyxtemp_folder):
    os.makedirs(pyxtemp_folder)

# Ensure PYTHONPATH includes the project root for locating orderbook.pyx
import sys
# Get the directory of the current test file (e.g., /path/to/project/tests)
current_dir = os.path.dirname(os.path.abspath(__file__))
# Get the parent directory (e.g., /path/to/project)
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

pyximport.install(build_dir=pyxtemp_folder, pyimport=True)

# Assuming orderbook.pyx is in the parent directory relative to the tests folder
# or the package structure makes it directly importable.
# If run via `python -m pytest`, PYTHONPATH should handle this.

# For robust testing, ensure PYTHONPATH includes the project root.
# One way to do this if running tests directly and `orderbook` is in parent dir:
# import sys
# sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from orderbook import OrderBook

# Strategies for generating test data
# Prices and quantities should be positive. For simplicity, using floats.
# In a real system, use decimal types or scaled integers for price levels.
prices_st = st.floats(min_value=0.1, max_value=100000, allow_nan=False, allow_infinity=False)
quantities_st = st.floats(min_value=0.001, max_value=1000, allow_nan=False, allow_infinity=False)

# Pytest fixture removed as Hypothesis needs fresh instances per example
# @pytest.fixture
# def book() -> OrderBook:
#     return OrderBook()

class TestOrderBookInitialization:
    def test_initial_book_is_empty(self):
        book = OrderBook() # Instantiate here
        assert book.get_bids() == {}
        assert book.get_asks() == {}
        assert book.get_best_bid() == pytest.approx(0.0)
        assert book.get_best_ask() == pytest.approx(0.0)

class TestOrderBookUpdates:
    @given(price=prices_st, quantity=quantities_st)
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_add_bid(self, price: float, quantity: float):
        book = OrderBook()
        book.update_bid(price, quantity)
        
        retrieved_bids = book.get_bids()
        assert len(retrieved_bids) == 1
        
        actual_price = list(retrieved_bids.keys())[0]
        actual_quantity = retrieved_bids[actual_price]
        
        assert actual_price == pytest.approx(price)
        assert actual_quantity == pytest.approx(quantity)
        assert book.get_bid_quantity(price) == pytest.approx(quantity) # Check direct lookup as well
        assert book.get_best_bid() == pytest.approx(price)

    @given(price=prices_st, quantity=quantities_st)
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_add_ask(self, price: float, quantity: float):
        book = OrderBook()
        book.update_ask(price, quantity)
        
        retrieved_asks = book.get_asks()
        assert len(retrieved_asks) == 1
        
        actual_price = list(retrieved_asks.keys())[0]
        actual_quantity = retrieved_asks[actual_price]
        
        assert actual_price == pytest.approx(price)
        assert actual_quantity == pytest.approx(quantity)
        assert book.get_ask_quantity(price) == pytest.approx(quantity) # Check direct lookup as well
        assert book.get_best_ask() == pytest.approx(price)

    @given(price=prices_st, initial_qty=quantities_st, updated_qty=quantities_st)
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_update_bid_quantity(self, price: float, initial_qty: float, updated_qty: float):
        book = OrderBook()
        book.update_bid(price, initial_qty)
        book.update_bid(price, updated_qty)
        assert book.get_bid_quantity(price) == pytest.approx(updated_qty)

    @given(price=prices_st, initial_qty=quantities_st, updated_qty=quantities_st)
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_update_ask_quantity(self, price: float, initial_qty: float, updated_qty: float):
        book = OrderBook()
        book.update_ask(price, initial_qty)
        book.update_ask(price, updated_qty)
        assert book.get_ask_quantity(price) == pytest.approx(updated_qty)

    @given(price=prices_st, quantity=quantities_st)
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_remove_bid(self, price: float, quantity: float):
        book = OrderBook()
        book.update_bid(price, quantity)
        book.update_bid(price, 0.0)
        assert book.get_bid_quantity(price) == pytest.approx(0.0)
        assert price not in book.get_bids() # Check key absence directly

    @given(price=prices_st, quantity=quantities_st)
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_remove_ask(self, price: float, quantity: float):
        book = OrderBook()
        book.update_ask(price, quantity)
        book.update_ask(price, 0.0)
        assert book.get_ask_quantity(price) == pytest.approx(0.0)
        assert price not in book.get_asks()

class TestBestBidAsk:
    @given(bid1_p=st.floats(min_value=10, max_value=20, allow_nan=False, allow_infinity=False), bid1_q=quantities_st,
           bid2_p=st.floats(min_value=21, max_value=30, allow_nan=False, allow_infinity=False), bid2_q=quantities_st)
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_best_bid_is_highest(self, bid1_p, bid1_q, bid2_p, bid2_q):
        book = OrderBook()
        book.update_bid(bid1_p, bid1_q)
        book.update_bid(bid2_p, bid2_q)
        assert book.get_best_bid() == pytest.approx(max(bid1_p, bid2_p))

    @given(ask1_p=st.floats(min_value=101, max_value=110, allow_nan=False, allow_infinity=False), ask1_q=quantities_st,
           ask2_p=st.floats(min_value=111, max_value=120, allow_nan=False, allow_infinity=False), ask2_q=quantities_st)
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_best_ask_is_lowest(self, ask1_p, ask1_q, ask2_p, ask2_q):
        book = OrderBook()
        book.update_ask(ask1_p, ask1_q)
        book.update_ask(ask2_p, ask2_q)
        assert book.get_best_ask() == pytest.approx(min(ask1_p, ask2_p))

    def test_best_bid_empty_book(self):
        book = OrderBook()
        assert book.get_best_bid() == pytest.approx(0.0)

    def test_best_ask_empty_book(self):
        book = OrderBook()
        assert book.get_best_ask() == pytest.approx(0.0)

    @given(price=st.floats(min_value=1.1, max_value=100000, allow_nan=False, allow_infinity=False), quantity=quantities_st)
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_best_bid_after_removal(self, price: float, quantity: float):
        book = OrderBook()
        # Add a lower bid first, then the target bid, then remove target bid
        lower_bid_price = price - 1 # This will be > 0 due to price strategy
        book.update_bid(lower_bid_price, quantity + 1)
        book.update_bid(price, quantity) # Add the higher bid
        book.update_bid(price, 0) # Remove the higher bid
        assert book.get_best_bid() == pytest.approx(lower_bid_price)

    @given(price=prices_st, quantity=quantities_st)
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_best_ask_after_removal(self, price: float, quantity: float):
        book = OrderBook()
        higher_ask_price = price + 1
        book.update_ask(higher_ask_price, quantity + 1)
        book.update_ask(price, quantity) # Add the lower ask
        book.update_ask(price, 0) # Remove the lower ask
        assert book.get_best_ask() == pytest.approx(higher_ask_price)

class TestBookTickerUpdate:
    @given(b=st.decimals(min_value="100.0", max_value="100.5", places=2).map(str),
           B=st.decimals(min_value="1.0", max_value="10.0", places=2).map(str),
           a=st.decimals(min_value="100.6", max_value="101.0", places=2).map(str),
           A=st.decimals(min_value="1.0", max_value="10.0", places=2).map(str),
           s=st.just("BTCUSDT"), u=st.integers())
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_update_from_book_ticker_data(self, b, B, a, A, s, u):
        book = OrderBook()
        ticker_data = {'b': b, 'B': B, 'a': a, 'A': A, 's': s, 'u': u}
        
        # Pre-populate with some other data that should be wiped by update_from_book_ticker
        book.update_bid(float(b) - 10.0, 5.0) 
        book.update_ask(float(a) + 10.0, 5.0)

        book.update_from_book_ticker(ticker_data)

        assert book.get_best_bid() == pytest.approx(float(b))
        assert book.get_bid_quantity(float(b)) == pytest.approx(float(B))
        assert book.get_best_ask() == pytest.approx(float(a))
        assert book.get_ask_quantity(float(a)) == pytest.approx(float(A))
        assert len(book.get_bids()) == 1
        assert len(book.get_asks()) == 1

    def test_update_from_book_ticker_clears_previous_top(self):
        book = OrderBook()
        book.update_bid(100.0, 10.0)
        book.update_ask(101.0, 5.0)
        assert book.get_best_bid() == pytest.approx(100.0)
        assert book.get_best_ask() == pytest.approx(101.0)

        ticker_data = {'b': '100.5', 'B': '12.0', 'a': '101.5', 'A': '6.0', 's': 'BTCUSDT', 'u': 12345}
        book.update_from_book_ticker(ticker_data)

        assert book.get_best_bid() == pytest.approx(100.5)
        assert book.get_bid_quantity(100.5) == pytest.approx(12.0)
        assert book.get_best_ask() == pytest.approx(101.5)
        assert book.get_ask_quantity(101.5) == pytest.approx(6.0)
        assert 100.0 not in book.get_bids()
        assert 101.0 not in book.get_asks()
        assert len(book.get_bids()) == 1
        assert len(book.get_asks()) == 1

# To run these tests: `pytest` in the terminal in the project root directory.
# Ensure Cython modules can be compiled (e.g., C++ compiler available). 