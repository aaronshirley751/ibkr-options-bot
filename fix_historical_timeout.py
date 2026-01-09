"""
Quick fix for historical data timeouts.
Updates the historical_prices method to accept and use a timeout parameter.
"""
import re

# Read the file
with open('src/bot/broker/ibkr.py', 'r') as f:
    content = f.read()

# Fix 1: Update method signature to add timeout parameter
old_sig = '''    def historical_prices(
        self,
        symbol: str,
        duration: str = "3600 S",
        bar_size: str = "1 min",
        what_to_show: str = "TRADES",
        use_rth: bool = True,
    ):'''

new_sig = '''    def historical_prices(
        self,
        symbol: str,
        duration: str = "3600 S",
        bar_size: str = "1 min",
        what_to_show: str = "TRADES",
        use_rth: bool = True,
        timeout: int = 60,
    ):'''

content = content.replace(old_sig, new_sig)

# Fix 2: Update docstring to include timeout
old_doc = '''        """Fetch historical OHLCV bars as a pandas DataFrame indexed by time.

        Args:
            symbol: Underlying stock symbol.
            duration: IBKR duration string in seconds or days (e.g., '3600 S' for 1 hour, '1 D' for 1 day).
            bar_size: IBKR bar size (e.g., '1 min', '5 mins', '1 hour').
            what_to_show: Data type, default 'TRADES'.
            use_rth: Restrict to Regular Trading Hours.

        Returns:
            pd.DataFrame with columns [open, high, low, close, volume] indexed by timestamp.
        """'''

new_doc = '''        """Fetch historical OHLCV bars as a pandas DataFrame indexed by time.

        Args:
            symbol: Underlying stock symbol.
            duration: IBKR duration string in seconds or days (e.g., '3600 S' for 1 hour, '1 D' for 1 day).
            bar_size: IBKR bar size (e.g., '1 min', '5 mins', '1 hour').
            what_to_show: Data type, default 'TRADES'.
            use_rth: Restrict to Regular Trading Hours.
            timeout: Max seconds to wait for historical data (default 60s for market hours reliability).

        Returns:
            pd.DataFrame with columns [open, high, low, close, volume] indexed by timestamp.
        """'''

content = content.replace(old_doc, new_doc)

# Fix 3: Wrap reqHistoricalData with timeout handling
old_call = '''            contract = Stock(symbol, "SMART", "USD")
            bars = self.ib.reqHistoricalData(
                contract,
                endDateTime="",
                durationStr=duration,
                barSizeSetting=bar_size,
                whatToShow=what_to_show,
                useRTH=use_rth,
                formatDate=1,
            )'''

new_call = '''            contract = Stock(symbol, "SMART", "USD")
            # Set request timeout for market hours: ib_insync default (~10s) insufficient during high load
            # 60s is conservative but necessary during peak market hours when Gateway is busy
            old_timeout = self.ib.RequestTimeout
            self.ib.RequestTimeout = timeout
            try:
                bars = self.ib.reqHistoricalData(
                    contract,
                    endDateTime="",
                    durationStr=duration,
                    barSizeSetting=bar_size,
                    whatToShow=what_to_show,
                    useRTH=use_rth,
                    formatDate=1,
                )
            finally:
                # Reset timeout to default for other operations
                self.ib.RequestTimeout = old_timeout'''

content = content.replace(old_call, new_call)

# Write the fixed file
with open('src/bot/broker/ibkr.py', 'w') as f:
    f.write(content)

print("✓ Fixed historical_prices timeout handling")
print("  - Added timeout parameter (default 60s)")
print("  - Set IB.RequestTimeout for historical data requests")
print("  - Reset timeout after request completes")

