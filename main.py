import asyncio
import logging
import os
from app.bot.main import main as start_bot
from app.forwarder.main import main as start_forwarder

# Create logs directory if it doesn't exist
if not os.path.exists("logs"):
    os.makedirs("logs")

# Clear the log file
with open("logs/bot.log", "w") as f:
    pass

# Enable logging
logging.basicConfig(
    force=True,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler("logs/bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
logger.info("Logging configured. This should appear in the log file.")

async def main():
    """Runs the bot and the forwarder services concurrently."""
    logger.info("Starting both bot and forwarder services...")
    
    # A dictionary to hold the running forwarder tasks
    forwarder_tasks = {}
    
    bot_task = asyncio.create_task(start_bot(forwarder_tasks))
    forwarder_task = asyncio.create_task(start_forwarder(forwarder_tasks))
    
    await asyncio.gather(bot_task, forwarder_task)

if __name__ == "__main__":
    asyncio.run(main())