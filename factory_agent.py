import time
import asyncio
import datetime
from spade import quit_spade
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour


class FactoryAgent(Agent):

    class TickerBehav(CyclicBehaviour):
        def __init__(self, progress_callback):
            super().__init__()
            self.progress_callback = progress_callback
            self.sleep_period = 1
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

    def __init__(self, jid, password, verify_security=False):
        super().__init__(jid, password, verify_security=False)
        self.ticker_behav = None
        self.progress_callback = None

    async def setup(self):
        print(f"TickerAgent started at {datetime.datetime.now().time()}")
        if self.progress_callback is None:
            raise Exception("progress callback not set")

        self.ticker_behav = self.TickerBehav(self.progress_callback)
        self.add_behaviour(self.ticker_behav)

    def set_progress_callback(self, callback):
        self.progress_callback = callback


# def main():
#     factory = FactoryAgent("agent@localhost", "password")
#     future = factory.start()
#     future.result()
#
#     while not factory.ticker_behav.is_killed():
#         try:
#             time.sleep(1)
#         except KeyboardInterrupt:
#             factory.stop()
#             break
#
#     print("Agent finished")
#     future = factory.stop()
#     future.result()
#     quit_spade()
#
#
# if __name__ == "__main__":
#     main()
