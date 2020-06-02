# kolekcja adresów
# handlery do menadżera
# wiadomości do gui

import asyncio
import datetime
import random

from spade import quit_spade
from spade.agent import Agent
from spade.behaviour import PeriodicBehaviour, OneShotBehaviour
from spade.message import Message

import settings
from common import Order, Point
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
    class StartAgents(OneShotBehaviour):
        """
        Starts all other agents.
        """

        async def run(self):
            # await a.start(auto_register=False)
            pass

    class OrderBehav(PeriodicBehaviour):
        """
        Cyclically generates orders and sends them to Manager Agent.
        """

        def __init__(self):
            super().__init__(10)

        async def run(self):
            # print(f"Running {type(self).__name__}...")

            order = self.agent.order_factory.create()

            # Send request
            msg = Message(to=f"manager@{settings.HOST}")
            msg.set_metadata("performative", "request")
            msg.body = f"{order}"  # Set the message content

            await self.send(msg)
            print(f"Message sent!\n{msg}")

            # set exit_code for the behaviour
            self.exit_code = "Job Finished!"

            self.agent.update_callback.emit(order.id)  # tmp: Emit progress signal with int

    def __init__(self, jid, password, verify_security=False):
        super().__init__(jid, password, verify_security=False)
        # Orders
        self.unused_id = 1
        self.orders = []
        self.order_factory = OrderFactory()
        self.order_behav = None

        self.update_callback = None

        # manager/factory address: {*}@{HOST}
        # tr/gom address: {*_base}{id}@{HOST}
        self.base_addresses = {
            "tr_base": "tr-",
            "gom_base": "gom-",
            "manager": "manager",
            "factory": "factory",
        }

        # GoM IDs start with 1, so that 0 can be used as set-aside's ID
        self.gom_count = 12
        self.gom_positions = [Point(x=-128.0, y=0.0)]  # [0] is set-aside position
        self.tr_positions = [Point(x=0.0, y=0.0)]  # [0] is a placeholder
        self.create_positions()

    async def setup(self):
        print(f"TickerAgent started at {datetime.datetime.now().time()}")
        if self.update_callback is None:
            raise Exception("update_callback not set")

        self.order_behav = self.OrderBehav()
        self.add_behaviour(self.order_behav)

    def set_update_callback(self, callback) -> None:
        """
        Sets callback used for updating GUI.
        :param callback: callback
        """
        self.update_callback = callback

    def create_positions(self):
        per_col = 5
        spray_diameter = 10
        for i in range(self.gom_count):
            y = (i % per_col) * 48 - 96
            x = int(i / per_col) * 64 - 32
            xo = random.gauss(0, spray_diameter)
            yo = random.gauss(0, spray_diameter)
            self.gom_positions.append(Point(x=x, y=y))
            self.tr_positions.append(Point(x=x+xo, y=y+yo))
