import time
import asyncio
import datetime
from spade import quit_spade
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour


class TickerAgent(Agent):

    class TickerBehav(CyclicBehaviour):
        def __init__(self, progress_callback):
            super().__init__()
            self.progress_callback = progress_callback
            self.sleep_period = 2
            self.counter = 0
            self.limit = 10

        async def on_start(self):
            print("Starting behaviour . . .")

        async def run(self):
            self.progress_callback.emit(self.counter) # Emit progress signal with int
            print(f"[TickerBehav] Counter: {self.counter}")
            self.counter += 1

            if self.counter == self.limit:
                self.kill(exit_code=0)
                return
            await asyncio.sleep(self.sleep_period)

        async def on_end(self):
            print(f"Behaviour finished with exit code {self.exit_code}.")

    def __init__(self, jid, password, progress_callback, verify_security=False):
        super().__init__(jid, password, verify_security=False)
        self.ticker_behav = None
        self.progress_callback_fn = progress_callback

    async def setup(self):
        print(f"TickerAgent started at {datetime.datetime.now().time()}")
        self.ticker_behav = self.TickerBehav(self.progress_callback_fn)
        self.add_behaviour(self.ticker_behav)


# def main():
#     ticker = TickerAgent("agent@localhost", "password")
#     future = ticker.start()
#     future.result()
#
#     while not ticker.ticker_behav.is_killed():
#         try:
#             time.sleep(1)
#         except KeyboardInterrupt:
#             ticker.stop()
#             break
#
#     print("Agent finished")
#     future = ticker.stop()
#     future.result()
#     quit_spade()
#
#
# if __name__ == "__main__":
#     main()
