# GHCR Authentication Instructions for Pi
# Run these commands on your Pi to authenticate with GitHub Container Registry

# 1. Create GitHub Personal Access Token (PAT)
# - Go to: https://github.com/settings/tokens
# - Click "Generate new token (classic)"
# - Select scopes: read:packages
# - Copy the generated token

# 2. Login to GHCR on Pi
echo "YOUR_PAT_TOKEN" | docker login ghcr.io -u YOUR_GITHUB_USERNAME --password-stdin

# 3. Test the original Gateway image
docker pull ghcr.io/gyrasol/ibkr-gateway:latest

# 4. If successful, run Gateway
cd ~/ibkr-options-bot
make gateway-up

# Commands to execute on Pi:
ssh pi@192.168.7.117
cd ibkr-options-bot

# Backup current config
cp docker-compose.gateway.yml docker-compose.gateway.yml.backup

# Try GHCR auth
echo "YOUR_PAT_HERE" | docker login ghcr.io -u YOUR_GITHUB_USERNAME --password-stdin
docker pull ghcr.io/gyrasol/ibkr-gateway:latest
make gateway-up
