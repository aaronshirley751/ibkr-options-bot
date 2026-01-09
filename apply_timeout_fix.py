#!/usr/bin/env python3
"""Apply historical data timeout fix to src/bot/broker/ibkr.py"""

with open('src/bot/broker/ibkr.py', 'r') as f:
    lines = f.readlines()

# Find and modify the historical_prices method signature
output_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    
    # Find the method definition and add timeout parameter
    if 'def historical_prices(' in line:
        # Output lines until we find the closing )
        output_lines.append(line)  # def historical_prices(
        i += 1
        while i < len(lines) and ')' not in lines[i]:
            if 'use_rth: bool = True,' in lines[i]:
                # Add timeout parameter after use_rth
                output_lines.append(lines[i])  # use_rth line
                i += 1
                output_lines.append('        timeout: int = 60,\n')
            else:
                output_lines.append(lines[i])
                i += 1
        output_lines.append(lines[i])  # closing ):
        i += 1
        
        # Update docstring to add timeout parameter
        while i < len(lines) and '"""' not in lines[i]:
            output_lines.append(lines[i])
            i += 1
        
        # Found opening docstring
        output_lines.append(lines[i])  # Opening """
        i += 1
        
        # Copy docstring content until Args section
        while i < len(lines) and 'Args:' not in lines[i]:
            output_lines.append(lines[i])
            i += 1
        
        output_lines.append(lines[i])  # Args:
        i += 1
        
        # Copy args until we find use_rth
        while i < len(lines) and 'use_rth:' not in lines[i]:
            output_lines.append(lines[i])
            i += 1
        
        # Found use_rth, output it and add timeout after
        output_lines.append(lines[i])  # use_rth: line
        i += 1
        
        # Skip the next line (continue of use_rth description if any) and add timeout instead
        output_lines.append('            timeout: Max seconds to wait for historical data (default 60s for market hours reliability).\n')
        
        while i < len(lines) and not (lines[i].strip().startswith('Returns:') or 'Returns:' in lines[i]):
            i += 1
        
        # Output rest of docstring
        while i < len(lines) and '"""' not in lines[i]:
            output_lines.append(lines[i])
            i += 1
        
        if i < len(lines):
            output_lines.append(lines[i])  # Closing """
            i += 1
        
        # Now find reqHistoricalData call and wrap it with timeout
        while i < len(lines) and 'contract = Stock(symbol' not in lines[i]:
            output_lines.append(lines[i])
            i += 1
        
        # Found contract line
        output_lines.append(lines[i])  # contract = Stock line
        i += 1
        
        # Add timeout handling before reqHistoricalData
        output_lines.append('            # Set request timeout for market hours: ib_insync default (~10s) insufficient during high load\n')
        output_lines.append('            # 60s is conservative but necessary during peak market hours when Gateway is busy\n')
        output_lines.append('            old_timeout = self.ib.RequestTimeout\n')
        output_lines.append('            self.ib.RequestTimeout = timeout\n')
        output_lines.append('            try:\n')
        
        # Skip blank lines and find bars = self.ib.reqHistoricalData(
        while i < len(lines) and 'bars = self.ib.reqHistoricalData(' not in lines[i]:
            if lines[i].strip():  # Skip blank lines
                break
            i += 1
        
        # Indent the reqHistoricalData call by 4 spaces (one more level)
        while i < len(lines) and ')' not in lines[i]:
            output_lines.append('    ' + lines[i])  # Add 4 spaces
            i += 1
        
        # Found closing ) of reqHistoricalData
        output_lines.append('    ' + lines[i])  # Add 4 spaces to closing )
        i += 1
        
        # Add finally block
        output_lines.append('            finally:\n')
        output_lines.append('                # Reset timeout to default for other operations\n')
        output_lines.append('                self.ib.RequestTimeout = old_timeout\n')
    else:
        output_lines.append(line)
        i += 1

# Write the fixed file
with open('src/bot/broker/ibkr.py', 'w') as f:
    f.writelines(output_lines)

print('✓ Applied timeout fix to historical_prices')
