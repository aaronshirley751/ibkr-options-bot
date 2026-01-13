#!/usr/bin/env python
"""
Diagnostic script to test IBKR data retrieval in real-time.
Run this to verify the bot can actually get bars during market hours.
"""

import sys
import time
from datetime import datetime
from ib_insync import IB, Stock

print("\n" + "="*80)
print("IBKR DIAGNOSTIC TEST - Historical Data Retrieval")
print("="*80)

try:
    print("\n[1] Current Time Check")
    now = datetime.now()
    print(f"    Local time: {now.strftime('%I:%M %p')}")
    print(f"    Eastern time: {datetime.utcnow().strftime('%I:%M %p')} (UTC)")
    
    print("\n[2] Connecting to IB Gateway...")
    ib = IB()
    ib.connect('192.168.7.205', 4001, clientId=999, timeout=20)
    print(f"    ✓ Connected: {ib.isConnected()}")
    
    print("\n[3] Checking IB Status...")
    print(f"    Qualifications available: {ib.qualifyContracts is not None}")
    print(f"    RequestTimeout: {ib.RequestTimeout}s")
    
    print("\n[4] Qualifying Contract for SPY...")
    contract = Stock('SPY', 'SMART', 'USD')
    qualified = ib.qualifyContracts(contract)
    print(f"    ✓ Contract qualified: {contract.conId}")
    
    print("\n[5] Requesting Historical Data (1 hour, 1-min bars)...")
    print(f"    Parameters:")
    print(f"      - Symbol: SPY")
    print(f"      - Duration: 3600 S (1 hour)")
    print(f"      - Bar Size: 1 min")
    print(f"      - Use RTH: True")
    print(f"      - What to Show: TRADES")
    
    request_start = time.time()
    bars = ib.reqHistoricalData(
        contract,
        endDateTime='',
        durationStr='3600 S',
        barSizeSetting='1 min',
        whatToShow='TRADES',
        useRTH=True,
        formatDate=1
    )
    elapsed = time.time() - request_start
    
    print(f"\n    Result:")
    print(f"      ✓ Elapsed time: {elapsed:.2f}s")
    print(f"      ✓ Bars retrieved: {len(bars) if bars else 0}")
    
    if bars and len(bars) > 0:
        print(f"\n[6] Sample Data (First 3 bars):")
        for i, bar in enumerate(bars[:3]):
            print(f"      {i+1}. {bar.date} | O:{bar.open} H:{bar.high} L:{bar.low} C:{bar.close} V:{bar.volume}")
        
        print(f"\n[7] Latest Bars (Last 3):")
        for i, bar in enumerate(bars[-3:]):
            print(f"      {i+1}. {bar.date} | O:{bar.open} H:{bar.high} L:{bar.low} C:{bar.close} V:{bar.volume}")
        
        print("\n✅ SUCCESS: Data retrieved successfully!")
        print(f"   The bot should be able to get bars during market hours.")
        
    else:
        print(f"\n❌ FAILURE: No bars returned!")
        print(f"   elapsed={elapsed:.2f}s, bars={len(bars) if bars else 0}")
        print(f"\n   Possible causes:")
        print(f"   1. Market is closed (check time above)")
        print(f"   2. Contract not properly qualified")
        print(f"   3. Data subscription missing")
        print(f"   4. Gateway connection issue")
    
    print("\n[8] Disconnecting...")
    ib.disconnect()
    print("    ✓ Done")
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)
