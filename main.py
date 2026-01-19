from src.discord_bot import KnowledgeBot
from src.config import DISCORD_TOKEN

if __name__ == "__main__":
    if not DISCORD_TOKEN:
        print("❌ DISCORD_TOKEN is not set in environment variables.")
    else:
        bot = KnowledgeBot()
        bot.run(DISCORD_TOKEN)
