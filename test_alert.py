from src.bot.settings import get_settings
from src.bot.monitoring import alert_all

def test_discord_alert():
    print("Loading settings...")
    settings = get_settings()
    
    # Get raw dictionary for alert_all compatibility
    settings_dict = settings.model_dump()
    
    webhook = settings_dict.get("monitoring", {}).get("discord_webhook_url")
    print(f"Testing Webhook: {webhook}")
    
    if not webhook:
        print("❌ Error: No Discord Webhook configured in configs/settings.yaml")
        return

    print("Sending test message...")
    try:
        alert_all(settings_dict, "🔔 **Test Message** from IBKR Whale Bot. If you see this, notifications are working! 🚀")
        print("✅ Notification sent to alert_all() function.")
        print("Check your Discord channel now.")
    except Exception as e:
        print(f"❌ Failed to send: {e}")

if __name__ == "__main__":
    test_discord_alert()
