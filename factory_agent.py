import asyncio
import datetime
import json
import random

from spade import quit_spade
from spade.agent import Agent
from spade.behaviour import PeriodicBehaviour, CyclicBehaviour
from spade.message import Message

from common import Order
from enums import Operation


class OrderFactory:
    """
    Creates `Orders`.
    """

    def __init__(self):
        self.unused_id = 1
        self.op_list = list(Operation)

    def create(self) -> Order:
        ops = [random.choice(self.op_list) for i in range(4)]
        order = Order(
            priority=1,
            id=self.unused_id,
            status=0,
            operations=ops
        )

        self.unused_id += 1

        return order


class FactoryAgent(Agent):

    class OrderBehav(PeriodicBehaviour):
        """
        Cyclically generates orders and sends them to Manager Agent.
        """

        def __init__(self):
            super().__init__(10)

        async def run(self):
            # print(f"Running {type(self).__name__}...")

            # Czy to jest dobre podejście?
            order = self.agent.order_factory.create()

            # Send request
            msg = Message(to="manager@localhost")
            msg.set_metadata("performative", "request")
            # msg.set_metadata("ontology", "myOntology")  # Set the ontology of the message content
            # msg.set_metadata("language", "OWL-S")  # Set the language of the message content
            msg.body = f"{order}"  # Set the message content

            await self.send(msg)
            print(f"Message sent!\n{msg}")

            # set exit_code for the behaviour
            self.exit_code = "Job Finished!"

            self.agent.progress_callback.emit(order.id)  # tmp: Emit progress signal with int

    def __init__(self, jid, password, verify_security=False):
        super().__init__(jid, password, verify_security=False)
        self.unused_id = 1
        self.orders = []
        self.order_factory = OrderFactory()

        self.order_behav = None

        self.progress_callback = None

    async def setup(self):
        print(f"TickerAgent started at {datetime.datetime.now().time()}")
        if self.progress_callback is None:
            raise Exception("progress callback not set")

        self.order_behav = self.OrderBehav()
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
