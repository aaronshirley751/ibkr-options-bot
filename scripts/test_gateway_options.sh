#!/bin/bash
# Gateway Resolution Script for Pi
# Run this on your Pi to try different Gateway options

set -e

echo "=== IBKR Gateway Resolution Script ==="
echo "Testing different Docker images for IB Gateway"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to test Gateway image
test_gateway() {
    local compose_file=$1
    local image_name=$2
    
    echo -e "${YELLOW}Testing: $image_name${NC}"
    
    # Try to pull the image
    if docker-compose -f "$compose_file" pull; then
        echo -e "${GREEN}✓ Successfully pulled $image_name${NC}"
        
        # Try to start the service
        if docker-compose -f "$compose_file" up -d; then
            echo -e "${GREEN}✓ Successfully started $image_name${NC}"
            sleep 10
            
            # Check if port 4002 is accessible
            if timeout 5 bash -c "</dev/tcp/localhost/4002"; then
                echo -e "${GREEN}✓ Port 4002 is accessible${NC}"
                echo -e "${GREEN}SUCCESS: $image_name is working!${NC}"
                
                # Test with ibkr connection script
                if [ -f "test_ibkr_connection.py" ]; then
                    echo "Testing IBKR connection..."
                    python test_ibkr_connection.py --host 127.0.0.1 --port 4002 --timeout 5
                fi
                
                docker-compose -f "$compose_file" down
                return 0
            else
                echo -e "${RED}✗ Port 4002 not accessible${NC}"
                docker-compose -f "$compose_file" down
                return 1
            fi
        else
            echo -e "${RED}✗ Failed to start $image_name${NC}"
            return 1
        fi
    else
        echo -e "${RED}✗ Failed to pull $image_name${NC}"
        return 1
    fi
}

# Backup original config
if [ -f "docker-compose.gateway.yml" ] && [ ! -f "docker-compose.gateway.yml.original" ]; then
    cp docker-compose.gateway.yml docker-compose.gateway.yml.original
    echo "Backed up original gateway config"
fi

echo ""
echo "=== Testing Gateway Options ==="

# Option 1: Try GHCR authentication first
echo ""
echo -e "${YELLOW}Option 1: GHCR Authentication${NC}"
echo "For this option, you need to authenticate with GitHub:"
echo "1. Create PAT at: https://github.com/settings/tokens"
echo "2. Select 'read:packages' scope"
echo "3. Run: echo 'YOUR_PAT' | docker login ghcr.io -u YOUR_USERNAME --password-stdin"
echo ""
read -p "Have you set up GHCR authentication? (y/n): " ghcr_auth

if [ "$ghcr_auth" = "y" ]; then
    if test_gateway "docker-compose.gateway.yml" "ghcr.io/gyrasol/ibkr-gateway:latest"; then
        echo -e "${GREEN}GHCR Gateway is working! No need to try alternatives.${NC}"
        exit 0
    fi
fi

# Option 2: Try vnexus image
echo ""
if test_gateway "docker-compose.gateway-vnexus.yml" "vnexus/ib-gateway:latest"; then
    echo -e "${GREEN}Found working alternative: vnexus/ib-gateway${NC}"
    cp docker-compose.gateway-vnexus.yml docker-compose.gateway.yml
    echo "Updated main gateway config to use vnexus image"
    exit 0
fi

# Option 3: Try universalappfactory image
echo ""
if test_gateway "docker-compose.gateway-uaf.yml" "universalappfactory/ib-gateway"; then
    echo -e "${GREEN}Found working alternative: universalappfactory/ib-gateway${NC}"
    cp docker-compose.gateway-uaf.yml docker-compose.gateway.yml
    echo "Updated main gateway config to use universalappfactory image"
    exit 0
fi

echo ""
echo -e "${RED}No working Gateway images found.${NC}"
echo "Next steps:"
echo "1. Set up GHCR authentication and try Option 1"
echo "2. Search for other public IB Gateway images"
echo "3. Consider manual IB Gateway installation"
echo ""
echo "For manual installation:"
echo "1. Download IB Gateway from IBKR website"
echo "2. Install on Pi directly (no Docker)"
echo "3. Configure to listen on port 4002"
