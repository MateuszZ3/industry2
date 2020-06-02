import asyncio
import datetime
import random

from spade.agent import Agent
from spade.behaviour import OneShotBehaviour, CyclicBehaviour, PeriodicBehaviour
from spade.message import Message
from spade.template import Template

import settings
from agents import GroupOfMachinesAgent, TransportRobotAgent
from common import Order, Point
from enums import Operation
from manager import Manager


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
            order_id=self.unused_id,
            current_operation=0,
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
            gom_infos = []
            for i, (gom_jid, tr_jid) in enumerate(self.agent.jids, start=1):
                gom_operations = list(Operation)
                gom_infos.append((gom_jid, gom_operations))
                gom = GroupOfMachinesAgent(manager_address=self.agent.manager_jid, tr_address=tr_jid,
                                           machines=gom_operations, jid=gom_jid, password=settings.PASSWORD)
                await gom.start()
                print(f'gom started {gom_jid=}')
                await asyncio.sleep(settings.AGENT_CREATION_SLEEP)
                tr = TransportRobotAgent(position=self.agent.tr_positions[i], gom_address=gom_jid,
                                         factory_map=self.agent.factory_map, jid=tr_jid, password=settings.PASSWORD)
                await tr.start()
                print(f'tr started {tr_jid=}')
                await asyncio.sleep(settings.AGENT_CREATION_SLEEP)

            manager = Manager(factory_jid=str(self.agent.jid), gom_infos=gom_infos, jid=self.agent.manager_jid,
                              password=settings.PASSWORD)
            await manager.start()
            print('manger')

    class OrderBehav(PeriodicBehaviour):
        """
        Cyclically generates orders and sends them to Manager Agent.
        """

        async def run(self):
            await self.agent.start_behaviour.join()
            print('after start')
            # print(f"Running {type(self).__name__}...")

            order = self.agent.order_factory.create()
            self.agent.orders[order.order_id] = order

            # Send request
            msg = Message(to=self.agent.manager_jid)
            msg.set_metadata("performative", "request")
            msg.body = order.to_json()  # Set the message content

            await self.send(msg)
            print(f"Message sent!\n{msg}")

            self.agent.update_callback.emit(order.order_id)  # tmp: Emit progress signal with int

    class OrderAgreeHandler(CyclicBehaviour):
        """
        On `agree` from `Manager`.
        """

        async def run(self):
            msg = await self.receive(timeout=settings.RECEIVE_TIMEOUT)
            if msg is not None:
                print(msg)

    class OrderFailureHandler(CyclicBehaviour):
        """
        On `failure` from `Manager`.
        """

        async def run(self):
            msg = await self.receive(timeout=settings.RECEIVE_TIMEOUT)
            if msg is not None:
                print(msg)

    class OrderDoneHandler(CyclicBehaviour):
        """
        On `inform` from `Manager`.
        """

        async def run(self):
            msg = await self.receive(timeout=settings.RECEIVE_TIMEOUT)
            if msg is not None:
                print(msg)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Orders
        self.unused_id = 1
        self.orders = {}
        self.order_factory = OrderFactory()
        self.order_behav = None

        self.update_callback = None

        self.manager_jid = f"{settings.AGENT_NAMES['manager']}@{settings.HOST}"

        # GoM IDs start with 1, so that 0 can be used as set-aside's ID
        self.gom_count = 12
        self.gom_positions = [Point(x=-128.0, y=0.0)]  # [0] is set-aside position
        self.tr_positions = [None]  # [0] is a placeholder
        self.factory_map = {
            '' : self.gom_positions[0]
        }
        self.jids = self.create()

        # Behaviours
        start_at = datetime.datetime.now() + datetime.timedelta(seconds=5)
        self.start_behaviour = self.StartAgents()
        self.order_behav = self.OrderBehav(5.0, start_at)
        self.agr_handler = self.OrderAgreeHandler()
        self.fail_handler = self.OrderFailureHandler()
        self.done_handler = self.OrderDoneHandler()

    async def setup(self):
        print(f"TickerAgent started at {datetime.datetime.now().time()}")
        if self.update_callback is None:
            raise Exception("update_callback not set")

        # Behaviours
        self.add_behaviour(self.start_behaviour)

        self.add_behaviour(self.order_behav)

        agr_temp = Template()
        agr_temp.sender = self.manager_jid
        agr_temp.metadata = {"performative": "agree"}
        self.add_behaviour(self.agr_handler, agr_temp)

        fail_temp = Template()
        fail_temp.sender = self.manager_jid
        fail_temp.metadata = {"performative": "failure"}
        self.add_behaviour(self.fail_handler, fail_temp)

        done_temp = Template()
        done_temp.sender = self.manager_jid
        done_temp.metadata = {"performative": "inform"}
        self.add_behaviour(self.done_handler, done_temp)

        self.add_behaviour(self.StartAgents())

    def set_update_callback(self, callback) -> None:
        """
        Sets callback used for updating GUI.
        :param callback: callback
        """
        self.update_callback = callback

    def create(self):
        per_col = 5
        spray_diameter = 10
        jids = []
        for i in range(self.gom_count):
            y = (i % per_col) * 48 - 96
            x = int(i / per_col) * 64 - 32
            xo = random.gauss(0, spray_diameter)
            yo = random.gauss(0, spray_diameter)
            self.gom_positions.append(Point(x=x, y=y))
            self.tr_positions.append(Point(x=x + xo, y=y + yo))
            gom_jid = f"{settings.AGENT_NAMES['gom_base']}{i + 1}@{settings.HOST}"
            tr_jid = f"{settings.AGENT_NAMES['tr_base']}{i + 1}@{settings.HOST}"
            jids.append((gom_jid, tr_jid))
            self.factory_map[gom_jid] = Point(x=x, y=y)
        return jids
