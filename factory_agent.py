import time
import asyncio
import datetime
from spade import quit_spade
from spade.agent import Agent
from spade.behaviour import OneShotBehaviour, CyclicBehaviour
from spade.message import Message

class Order:
    __unused_id = 1

    def __init__(self):
        self.id = Order.__unused_id
        Order.__unused_id += 1

    def __str__(self):
        return f"order id: {self.id}"


class VerboseCyclicBehaviour(CyclicBehaviour):
    async def on_start(self):
        print(f"Starting {type(self).__name__}...")

    async def on_end(self):
        print(f"{type(self).__name__} finished with exit code {self.exit_code}.")

    async def run(self):
        pass


class FactoryAgent(Agent):
    class TickerBehav(VerboseCyclicBehaviour):
        """
        tmp
        """

        def __init__(self, progress_callback):
            super().__init__()
            self.progress_callback = progress_callback
            self.sleep_period = 1
            self.counter = 0
            self.limit = 10

        async def run(self):
            self.progress_callback.emit(self.counter)  # Emit progress signal with int

            print(f"[TickerBehav] Counter: {self.counter}")
            self.counter += 1

            if self.counter == self.limit:
                self.kill(exit_code=0)
                return
            await asyncio.sleep(self.sleep_period)

    class OrderBehav(OneShotBehaviour):
        """
        Cyclically generates orders and sends them to Manager Agent.
        """

        def __init__(self):
            super().__init__()

        async def run(self):
            order = Order()

            # Send request
            msg = Message(to="manager@localhost")
            msg.set_metadata("performative", "request")
            # msg.set_metadata("ontology", "myOntology")  # Set the ontology of the message content
            # msg.set_metadata("language", "OWL-S")  # Set the language of the message content
            msg.body = f"{order}"  # Set the message content

            await self.send(msg)
            print("Message sent!")

            # set exit_code for the behaviour
            self.exit_code = "Job Finished!"


    def __init__(self, jid, password, verify_security=False):
        super().__init__(jid, password, verify_security=False)
        self.ticker_behav = None
        self.order_behav = None
        self.progress_callback = None
        self.orders = []

    async def setup(self):
        print(f"TickerAgent started at {datetime.datetime.now().time()}")
        if self.progress_callback is None:
            raise Exception("progress callback not set")

        self.ticker_behav = self.TickerBehav(self.progress_callback)
        self.order_behav = self.OrderBehav()
        self.add_behaviour(self.ticker_behav)
        self.add_behaviour(self.order_behav)

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
