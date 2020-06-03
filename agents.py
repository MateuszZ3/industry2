import asyncio
import datetime
import random
from asyncio import sleep
from collections import defaultdict
from dataclasses import dataclass
from heapq import heappop, heappush
from typing import List

from spade.agent import Agent
from spade.behaviour import OneShotBehaviour, CyclicBehaviour, PeriodicBehaviour
from spade.message import Message
from spade.template import Template

import settings
from common import GoMOrder
from common import Order, Point
from enums import Operation


@dataclass
class Machine:
    operation: Operation
    working: bool = True


@dataclass
class GoMInfo:
    jid: str
    machines: List[Machine]


@dataclass
class ActiveOrder:
    order: Order
    location: str  # "" - warehouse, "address@host" - socket_id

    def advance(self, loc: str):
        self.order.current_operation += 1
        self.location = loc


class RecvBehaviour(CyclicBehaviour):
    """
    Base receive handler behaviour.
    :param handler: Handler run when a message is received.
    """
    def __init__(self, handler):
        super().__init__()
        self.handler = handler

    async def run(self):
        msg = await self.receive(timeout=settings.RECEIVE_TIMEOUT)
        if msg is not None:
            await self.handler(msg, self)


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
                # Create and start GoM agent
                gom_operations = list(Operation)
                gom_infos.append((gom_jid, gom_operations))
                gom = GroupOfMachinesAgent(manager_address=self.agent.manager_jid, tr_address=tr_jid,
                                           machines=gom_operations, jid=gom_jid, password=settings.PASSWORD)
                await gom.start()
                print(f'gom started gom_jid={gom_jid}')
                await asyncio.sleep(settings.AGENT_CREATION_SLEEP)  # Wait around 100ms for registration to complete

                # Create and start TR agent
                tr = TransportRobotAgent(position=self.agent.tr_positions[i], gom_address=gom_jid,
                                         factory_map=self.agent.factory_map, jid=tr_jid, password=settings.PASSWORD)
                await tr.start()
                print(f'tr started tr_jid={tr_jid}')
                await asyncio.sleep(settings.AGENT_CREATION_SLEEP)  # Wait around 100ms for registration to complete

            # Create and start Manager agent
            manager = Manager(factory_jid=str(self.agent.jid), gom_infos=gom_infos, jid=self.agent.manager_jid,
                              password=settings.PASSWORD)
            await manager.start()

    class OrderBehav(PeriodicBehaviour):
        """
        Cyclically generates orders and sends them to Manager Agent.
        """

        async def run(self):
            await self.agent.start_behaviour.join()
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
        On `agree` message from `Manager`.
        """

        async def run(self):
            msg = await self.receive(timeout=settings.RECEIVE_TIMEOUT)
            if msg is not None:
                print(msg)

    class OrderFailureHandler(CyclicBehaviour):
        """
        On `failure` message from `Manager`.
        """

        async def run(self):
            msg = await self.receive(timeout=settings.RECEIVE_TIMEOUT)
            if msg is not None:
                print(msg)

    class OrderDoneHandler(CyclicBehaviour):
        """
        On `inform` message from `Manager`.
        """

        async def run(self):
            msg = await self.receive(timeout=settings.RECEIVE_TIMEOUT)
            if msg is not None:
                print(msg)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Orders
        self.unused_id = 1  # Currently unused Order ID
        self.orders = {}
        self.order_factory = OrderFactory()
        self.order_behav = None

        self.update_callback = None  # Callback used for updating GUI.

        # GoM IDs start with 1, so that 0 can be used as set-aside's ID
        self.gom_count = 12
        self.gom_positions = [Point(x=-128.0, y=0.0)]  # [0] is set-aside position
        self.tr_positions = [None]  # [0] is a placeholder
        # Maps JID to Point
        self.factory_map = {
            '': self.gom_positions[0]
        }

        # JIDs
        self.manager_jid = f"{settings.AGENT_NAMES['manager']}@{settings.HOST}"
        self.jids = self.prepare()

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

    def prepare(self):
        """
        Generates positions and JIDs for GoMs and TRs
        :return:
        """
        per_col = 5
        spray_diameter = 10
        jids = []
        for i in range(self.gom_count):
            # Create GoM and TR positions
            y = (i % per_col) * 48 - 96
            x = int(i / per_col) * 64 - 32
            xo = random.gauss(0, spray_diameter)
            yo = random.gauss(0, spray_diameter)
            self.gom_positions.append(Point(x=x, y=y))
            self.tr_positions.append(Point(x=x + xo, y=y + yo))

            # Create JIDs
            gom_jid = f"{settings.AGENT_NAMES['gom_base']}{i + 1}@{settings.HOST}"
            tr_jid = f"{settings.AGENT_NAMES['tr_base']}{i + 1}@{settings.HOST}"
            jids.append((gom_jid, tr_jid))
            self.factory_map[gom_jid] = Point(x=x, y=y)

        return jids


class Manager(Agent):
    class MainLoop(CyclicBehaviour):
        """
        Main agent loop. Takes an order from the queue, if available, updates its state and sends a request to a GoM.
        """

        async def on_start(self):
            print("Starting main loop . . .")

        async def run(self):
            if not self.agent.gom_infos:
                await sleep(settings.MANAGER_LOOP_TIMEOUT)
                return
            gom: GoMInfo = random.choice(self.agent.gom_infos)
            while not self.agent.orders:
                await sleep(0.1)
            order: Order = heappop(self.agent.orders)
            print(order)
            oid = str(order.order_id)
            if oid not in self.agent.active_orders:
                self.agent.active_orders[oid] = ActiveOrder(order, '')
            gorder = GoMOrder.create(order, self.agent.active_orders[oid].location)
            msg = Message(to=gom.jid)
            msg.set_metadata("performative", "request")
            msg.body = gorder.to_json()
            msg.thread = oid
            print(f'manager send: {msg}')
            await self.send(msg)

        async def on_end(self):
            print(f"{self.agent} finished main loop with exit code {self.exit_code}.")

    class OrderRequestHandler(CyclicBehaviour):
        """Request from factory"""

        async def run(self):
            msg = await self.receive(timeout=settings.RECEIVE_TIMEOUT)
            order = Order.from_json(msg.body)
            print(order)
            heappush(self.agent.orders, order)
            reply = Message(self.agent.factory_jid)
            reply.set_metadata("performative", "agree")
            await self.send(reply)

    class OrderRefuseHandler(CyclicBehaviour):
        """Refuse from GoM"""

        async def run(self):
            msg = await self.receive(timeout=settings.RECEIVE_TIMEOUT)
            oid = msg.thread
            active_order: ActiveOrder = self.agent.active_orders[oid]
            heappush(self.agent.orders, active_order.order)
            # self.agent.active_orders[oid] = None todo remove

    class OrderAgreeHandler(CyclicBehaviour):
        """Agree from GoM"""

        async def run(self):
            msg = await self.receive(timeout=settings.RECEIVE_TIMEOUT)
            print('agree received for order ' + msg.thread)
            return

    class OrderDoneHandler(CyclicBehaviour):
        """Inform from GoM"""

        async def run(self):
            msg = await self.receive(timeout=settings.RECEIVE_TIMEOUT)
            oid = msg.thread
            active_order: ActiveOrder = self.agent.active_orders[oid]
            active_order.advance(msg.sender)
            if not active_order.order.is_done():
                heappush(self.agent.orders, active_order.order)
            else:
                self.agent.active_orders[oid] = None
                report = Message(self.agent.factory_jid)
                report.set_metadata("performative", "inform")
                report.thread = oid
                await self.send(report)

    def __init__(self, factory_jid: str, gom_infos, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.gom_infos = []
        for gom_jid, operations in gom_infos:
            self.gom_infos.append(GoMInfo(jid=gom_jid, machines=[Machine(operation=op) for op in operations]))
        self.orders = []
        self.active_orders = {}  # todo zamiana na PQ, tylko z (prio, id)
        self.factory_jid = factory_jid
        self.main_loop = self.MainLoop()
        self.req_handler = self.OrderRequestHandler()
        self.ref_handler = self.OrderRefuseHandler()
        self.agr_handler = self.OrderAgreeHandler()
        self.done_handler = self.OrderDoneHandler()

    async def setup(self):
        print("Manager starting . . .")
        fac_temp = Template()
        fac_temp.sender = self.factory_jid
        fac_temp.metadata = {"performative": "request"}
        self.add_behaviour(self.req_handler, fac_temp)
        ref_temp = Template()
        ref_temp.metadata = {"performative": "refuse"}
        self.add_behaviour(self.ref_handler, ref_temp)
        agr_temp = Template()
        agr_temp.metadata = {"performative": "agree"}
        self.add_behaviour(self.agr_handler, agr_temp)
        done_temp = Template()
        done_temp.metadata = {"performative": "inform"}
        self.add_behaviour(self.done_handler, done_temp)
        self.add_behaviour(self.main_loop)


class GroupOfMachinesAgent(Agent):
    def __init__(self, manager_address, tr_address, machines, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.manager_address = manager_address
        self.tr_address = tr_address
        self.machines = defaultdict(list)
        for operation in machines:
            self.machines[operation].append(
                Machine(operation=operation, working=True))
        self.order = None
        self.msg_order = None

    class WorkBehaviour(OneShotBehaviour):
        async def run(self):
            assert self.agent.order is not None
            work_duration = settings.OP_DURATIONS[self.agent.order.operation]
            await asyncio.sleep(work_duration)

            assert self.agent.msg_order is not None
            reply = self.agent.msg_order.make_reply()
            reply.set_metadata('performative', 'inform')
            await self.send(reply)

            self.agent.order = None
            self.agent.msg_order = None

    def can_accept_order(self, order):
        if order.operation not in self.machines:
            return False
        return all([
            self.order is None,
            any(machine.working for machine in self.machines[order.operation])
        ])

    async def handle_tr_agree(self, msg, recv):
        assert msg is not None

    async def handle_tr_inform(self, msg, recv):
        assert msg is not None
        self.add_behaviour(self.WorkBehaviour())
        reply = self.msg_order.make_reply()
        reply.set_metadata('performative', 'inform')
        await recv.send(reply)

    async def handle_manager_request(self, msg, recv):
        reply = msg.make_reply()
        order = GoMOrder.from_json(msg.body)
        accepted = False
        if self.can_accept_order(order):
            assert self.msg_order is None
            self.order = order
            self.msg_order = msg
            reply.set_metadata('performative', 'agree')
            accepted = True
        else:
            reply.set_metadata('performative', 'refuse')
        await recv.send(reply)
        if accepted:
            if str(self.jid) == order.location:
                self.add_behaviour(self.WorkBehaviour())
            else:
                msg_tr = Message(to=self.tr_address)
                msg_tr.set_metadata('performative', 'request')
                msg_tr.body = msg.body
                await recv.send(msg_tr)

    async def setup(self):
        self.add_behaviour(
            behaviour=RecvBehaviour(self.handle_manager_request),
            template=Template(sender=self.manager_address, metadata={"performative": "request"})
        )
        self.add_behaviour(
            behaviour=RecvBehaviour(self.handle_tr_agree),
            template=Template(sender=self.tr_address, metadata={"performative": "agree"})
        )
        self.add_behaviour(
            behaviour=RecvBehaviour(self.handle_tr_inform),
            template=Template(sender=self.tr_address, metadata={"performative": "inform"})
        )


class TransportRobotAgent(Agent):
    def __init__(self, position, gom_address, factory_map, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.position = position
        self.gom_address = gom_address
        self.factory_map = factory_map
        self.order = None  # mother gom
        self.msg_order = None  # mother gom
        self.loaded_order = None

    class MoveBehaviour(PeriodicBehaviour):
        def __init__(self, destination, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.destination = destination
            self.counter = 0

        async def run(self):
            #  TODO real move
            if self.counter > 5:
                self.kill()
            self.counter += 1

    class AfterBehaviour(OneShotBehaviour):
        def __init__(self, behaviour, after_behaviour_fun):
            super().__init__()
            self.behaviour = behaviour
            self.after_behaviour_fun = after_behaviour_fun

        async def run(self):
            await self.behaviour.join()
            await self.after_behaviour_fun(self)

    def move(self, destination):
        move_behaviour = self.MoveBehaviour(destination, period=0.1)
        self.add_behaviour(move_behaviour)
        return move_behaviour

    def add_after_behaviour(self, behaviour, after_behaviour_fun):
        after_behaviour = self.AfterBehaviour(behaviour, after_behaviour_fun)
        self.add_behaviour(after_behaviour)
        return after_behaviour

    async def load_order(self, behaviour):
        assert self.loaded_order is None
        assert self.msg_order is not None
        assert self.order is not None
        self.loaded_order = self.order
        destination = self.factory_map[self.gom_address]
        move_behaviour = self.move(destination)
        self.add_after_behaviour(move_behaviour, self.deliver_order)

    async def deliver_order(self, behaviour):
        assert self.loaded_order is not None
        assert self.msg_order is not None
        assert self.order is not None
        reply = self.msg_order.make_reply()
        reply.set_metadata('performative', 'inform')
        await behaviour.send(reply)

        self.loaded_order = None
        self.msg_order = None
        self.order = None

    def get_order(self):
        destination = self.factory_map[self.order.location]
        move_behaviour = self.move(destination)
        self.add_after_behaviour(move_behaviour, self.load_order)

    async def handle_tr_request(self, msg, recv):
        assert self.msg_order is None
        assert self.order is None
        self.msg_order = msg
        self.order = GoMOrder.from_json(msg.body)
        reply = self.msg_order.make_reply()
        reply.set_metadata('performative', 'agree')
        await recv.send(reply)
        self.get_order()

    async def setup(self):
        self.add_behaviour(
            behaviour=RecvBehaviour(self.handle_tr_request),
            template=Template(sender=self.gom_address, metadata={"performative": "request"})
        )
