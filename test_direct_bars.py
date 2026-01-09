#!/usr/bin/env python3
"""
Direct ib_insync Historical Data Test
Purpose: Verify that historical bars are retrievable from Gateway outside the bot framework
Usage: python test_direct_bars.py
Expected: Should print current SPY price and ~60 bars from last hour
"""

from ib_insync import *
import sys
from datetime import datetime

def test_direct_bars():
    """Test direct historical data request from Gateway"""
    
    print("=" * 80)
    print("DIRECT ib_insync HISTORICAL DATA TEST")
    print("=" * 80)
    print(f"Time: {datetime.now()}")
    print()
    
    # Connect to Gateway
    print("[1/4] Connecting to Gateway at 192.168.7.205:4001...")
    ib = IB()
    try:
        ib.connect('192.168.7.205', 4001, clientId=999)
        print("✓ Connected successfully")
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return False
    
    print()
    
    # Test 1: Current market data
    print("[2/4] Testing current market data for SPY...")
    try:
        contract = Stock('SPY', 'SMART', 'USD')
        ib.qualifyContracts(contract)
        ticker = ib.reqMktData(contract)
        ib.sleep(1)  # Give API time to update
        
        print(f"  Symbol: {contract.symbol}")
        print(f"  Contract ID: {contract.conId}")
        print(f"  Last Price: {ticker.last}")
        print(f"  Bid: {ticker.bid} | Ask: {ticker.ask}")
        print(f"  Volume: {ticker.volume}")
        
        if ticker.last is None or ticker.last == 0:
            print("✗ WARNING: Last price is None/0 - data may not be subscribed")
        else:
            print("✓ Market data received")
    except Exception as e:
        print(f"✗ Market data failed: {e}")
        ib.disconnect()
        return False
    
    print()
    
    # Test 2: Historical data
    print("[3/4] Requesting 1 hour of 1-minute bars...")
    try:
        bars = ib.reqHistoricalData(
            contract,
            endDateTime='',  # Current time
            durationStr='3600 S',  # Last 3600 seconds (1 hour)
            barSizeSetting='1 min',
            whatToShow='TRADES',
            useRTH=True  # Regular trading hours only
        )
        
        print(f"  Bars returned: {len(bars)}")
        
        if len(bars) == 0:
            print("✗ CRITICAL: No bars returned - data subscription or request issue")
            ib.disconnect()
            return False
        elif len(bars) < 30:
            print(f"✗ WARNING: Only {len(bars)} bars (expected ~60)")
        else:
            print(f"✓ Sufficient bars returned ({len(bars)})")
        
        # Show sample bars
        print(f"\n  Last 5 bars:")
        for bar in bars[-5:]:
            print(f"    {bar.date.strftime('%H:%M:%S')} | O={bar.open:7.2f} H={bar.high:7.2f} L={bar.low:7.2f} C={bar.close:7.2f} V={int(bar.volume):8d}")
        
    except Exception as e:
        print(f"✗ Historical data request failed: {e}")
        import traceback
        traceback.print_exc()
        ib.disconnect()
        return False
    
    print()
    
    # Disconnect
    print("[4/4] Disconnecting...")
    ib.disconnect()
    print("✓ Disconnected")
    
    print()
    print("=" * 80)
    print("RESULT: ✓ TEST PASSED - Historical data is retrievable from Gateway")
    print("        Problem is likely in bot code, not Gateway/subscription")
    print("=" * 80)
    
    return True


if __name__ == '__main__':
    success = test_direct_bars()
    sys.exit(0 if success else 1)
