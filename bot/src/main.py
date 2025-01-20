import asyncio
import logging
import sys

from bot.start import create_dispatcher
from bot.utils import bot


async def main():
    dp = create_dispatcher()
    await dp.start_polling(bot)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
