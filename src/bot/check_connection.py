from ib_insync import IB
from .settings import get_settings
import sys

def check_connection():
    print("Checking IBKR Connection...")
    settings = get_settings()
    
    ip = settings.broker.host
    port = settings.broker.port
    cid = settings.broker.client_id
    
    print(f"Connecting to {ip}:{port} (ClientId: {cid})...")
    
    ib = IB()
    try:
        ib.connect(ip, port, clientId=cid, timeout=10)
        print("✅ Connection Successful!")
        print(f"Connected to: {ib.client.host}:{ib.client.port}")
        ib.disconnect()
        return True
    except Exception as e:
        print(f"❌ Connection Failed: {e}")
        return False

if __name__ == "__main__":
    success = check_connection()
    sys.exit(0 if success else 1)
