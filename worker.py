import asyncio

import worker

if __name__ == "__main__":
    try:
        asyncio.run(worker.run())
    except KeyboardInterrupt:
        print("Good night!")
