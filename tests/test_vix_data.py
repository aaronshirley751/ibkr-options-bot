import pytest
import asyncio
from src.bot.broker.ibkr import IBKRBroker
from ib_insync import Index

@pytest.mark.asyncio
async def test_vix_data_fetch():
    """Verify we can fetch VIX data from IBKR."""
    broker = IBKRBroker(host="192.168.7.205", port=4001, client_id=888)
    
    try:
        # Bypass synchronous wrapper which conflicts with pytest-asyncio loop
        # Connect asynchronously
        await broker.ib.connectAsync(broker.host, broker.port, broker.client_id)
        
        if not broker.ib.isConnected():
             pytest.skip("Could not connect to IBKR Gateway")

        # Define VIX Index contract
        vix = Index(symbol='VIX', exchange='CBOE')
        
        # Request market data
        logger_mock = None # Not needed for basic check
        
        # IBKR often requires qualifying contracts
        qualified = await broker.ib.qualifyContractsAsync(vix)
        assert len(qualified) == 1, "Could not qualify VIX contract"
        
        vix_contract = qualified[0]
        
        # Get market data
        ticker = broker.ib.reqMktData(vix_contract, '', False, False)
        
        # Wait for data (up to 5s)
        for _ in range(50):
            await asyncio.sleep(0.1)
            if ticker.last > 0 or ticker.close > 0 or ticker.bid > 0:
                break
                
        print(f"VIX Ticker: last={ticker.last}, close={ticker.close}")
        
        assert ticker.last > 0 or ticker.close > 0, "No valid VIX price received"
        
    finally:
        broker.disconnect()
