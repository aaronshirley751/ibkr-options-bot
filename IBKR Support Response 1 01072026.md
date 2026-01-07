	Initial Description: API Market Data Not Working (Live Account, Subs Active, Only Historical Data Works) — IB Gateway 10.37
Response from IBCS at 07-Jan-2026

Dear Mr. Shirley,

I can confirm that you are subscribed to:

US Equity and Options Add-On Streaming Bundle (NP)
US Securities Snapshot and Futures Value Bundle (NP,L1)

This will cover US equities and options.

The issue may be that you are using ib_insync, possibly. Please be aware that ib_insync is a third party package not affiliated with Interactive Brokers that is based on an old, unsupported release of the TWS API and you may experience more significant issues because of it. See https://www.interactivebrokers.com/campus/ibkr-api-page/twsapi-doc/#ib-insync for more information on this.

To test using the Official API:

1. Download the Stable/Latest version of the TWS API from https://interactivebrokers.github.io
2. Install the API as per https://www.interactivebrokers.com/campus/ibkr-api-page/twsapi-doc/#find-the-api i.e. navigate to the source/pythonclient directory and run the command 'pip install .' (Note the '.' indicating a local pip install)
3. Go to https://github.com/awiseib/Python-testers/tree/main/Live%20Data
4. Download the LiveData-top.py sample script
5. Alter the connection parameters as required i.e. port number etc
6. Run the script to check that all works okay with the connection and streaming live/delayed data.

You may then alter the contract details for testing.

Thank you.

Kind regards,
Keela
IBKR Client Services