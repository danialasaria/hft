# orderbook.pyx
# distutils: language = c++

# This file will contain the Cython implementation of the order book.
# It will use a price-level hash-map for O(log n) updates.
# For now, it's a placeholder.

import pyximport
pyximport.install()

from libc.stdint cimport int64_t
from libcpp.map cimport map as cpp_map
from cython.operator cimport dereference as deref, preincrement

# Using float for price and quantity for simplicity, though fixed-point decimals are better for finance.
cdef class OrderBook:
    cdef cpp_map[float, float] bids # price -> quantity
    cdef cpp_map[float, float] asks # price -> quantity

    def __init__(self):
        self.bids = cpp_map[float, float]()
        self.asks = cpp_map[float, float]()

    cpdef update_bid(self, float price, float quantity):
        """Updates or adds a bid. If quantity is 0, removes the price level."""
        if quantity == 0:
            if self.bids.count(price):
                self.bids.erase(price)
        else:
            self.bids[price] = quantity

    cpdef update_ask(self, float price, float quantity):
        """Updates or adds an ask. If quantity is 0, removes the price level."""
        if quantity == 0:
            if self.asks.count(price):
                self.asks.erase(price)
        else:
            self.asks[price] = quantity

    cpdef float get_best_bid(self):
        if self.bids.empty():
            return 0.0 # Or raise an error, or return None/NaN
        return deref(self.bids.rbegin()).first # Dereference iterator

    cpdef float get_best_ask(self):
        if self.asks.empty():
            return 0.0 # Or raise an error, or return None/NaN
        return deref(self.asks.begin()).first # Dereference iterator

    cpdef float get_bid_quantity(self, float price):
        if self.bids.count(price):
            return self.bids[price]
        return 0.0

    cpdef float get_ask_quantity(self, float price):
        if self.asks.count(price):
            return self.asks[price]
        return 0.0

    # For displaying the book (Python-callable)
    def get_bids(self):
        py_bids = {}
        cdef cpp_map[float, float].iterator it = self.bids.begin()
        while it != self.bids.end():
            py_bids[deref(it).first] = deref(it).second
            preincrement(it)
        return py_bids

    def get_asks(self):
        py_asks = {}
        cdef cpp_map[float, float].iterator it = self.asks.begin()
        while it != self.asks.end():
            py_asks[deref(it).first] = deref(it).second
            preincrement(it)
        return py_asks

    # The LOB reconstruction will primarily use bookTicker for top-of-book
    # and later diff-depth for updates beyond top-of-book.
    # For now, this simplified OrderBook will be updated by bookTicker data.
    def update_from_book_ticker(self, dict data):
        """Updates the order book from a Binance bookTicker stream message."""
        # For bookTicker, we only get top of book, so clear existing state.
        self.bids.clear()
        self.asks.clear()

        best_bid_price = float(data['b'])
        best_bid_qty = float(data['B'])
        best_ask_price = float(data['a'])
        best_ask_qty = float(data['A'])

        self.update_bid(best_bid_price, best_bid_qty)
        self.update_ask(best_ask_price, best_ask_qty)

# No trailing content after this line. 