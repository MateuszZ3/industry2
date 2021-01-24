import asyncio
from copy import deepcopy
import datetime
import json
import random
from asyncio import sleep
from collections import defaultdict
from dataclasses import dataclass
from heapq import heappop, heappush
from typing import Dict, List

import numpy as np
from spade.agent import Agent
from spade.behaviour import OneShotBehaviour, CyclicBehaviour, PeriodicBehaviour, FSMBehaviour, State
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


@dataclass(order=True)
class GoMInfo:
    jid: str
    machines: List[Machine]


@dataclass
class ActiveOrder:
    order: Order
    location: str  # "" - warehouse, "address@host" - gom_jid

    def advance(self, loc: str):
        self.order.current_operation += 1
        self.location = loc


class RecvBehaviour(CyclicBehaviour):
    """
    Base receive handler behaviour.

    :param handler: Handler run when a message is received (takes two arguments, msg - received message
        and recv - calling behaviour).
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
        ops_num = random.randint(3, 10)
        ops = [random.choice(self.op_list) for i in range(ops_num)]
        order = Order(
            priority=1,
            order_id=self.unused_id,
            current_operation=0,
            tr_count=[1] * ops_num,
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
                gom = GroupOfMachinesAgent(manager_jid=self.agent.manager_jid, tr_jid=tr_jid,
                                           machines=gom_operations, jid=gom_jid, password=settings.PASSWORD)
                await gom.start()
                print(f'gom started gom_jid={gom_jid}')
                # Wait around 100ms for registration to complete
                await asyncio.sleep(settings.AGENT_CREATION_SLEEP)

                # Create and start TR agent
                tr_jids = [tr for (_, tr) in self.agent.jids if tr != tr_jid]
                tr = TransportRobotAgent(position=self.agent.tr_map[tr_jid], gom_jid=gom_jid,
                                         factory_jid=str(self.agent.jid), factory_map=self.agent.factory_map,
                                         tr_jids=tr_jids, jid=tr_jid, password=settings.PASSWORD)
                self.agent.tr_list[tr_jid] = tr

                await tr.start()
                print(f'tr started tr_jid={tr_jid}')
                # Wait around 100ms for registration to complete
                await asyncio.sleep(settings.AGENT_CREATION_SLEEP)

            # Send data to worker
            self.agent.perform_view_model_update()
            # Start periodically updating positions
            self.agent.add_behaviour(self.agent.position_updater)
            self.agent.add_behaviour(self.agent.tr_list_updater)

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

    class PositionHandler(CyclicBehaviour):
        """
        On `inform` message from `TR` signifying position change.
        Position is sent in body as `Point`.
        """
        async def run(self):
            msg = await self.receive(timeout=settings.RECEIVE_TIMEOUT)
            if msg is not None:
                tr_jid = str(msg.sender)
                pos = Point.from_json(msg.body)
                self.agent.tr_map[tr_jid] = pos
                # Note: Positions are updated in bulk by PositionUpdater behaviour.
                # self.agent.update_tr_position.emit(tr_jid, pos)

    class PositionUpdater(PeriodicBehaviour):
        """Periodically updates TR positions."""
        async def run(self):
            tr_map_copy = deepcopy(self.agent.tr_map)
            self.agent.update_view_model.emit(None, tr_map_copy, None)

    class TRListUpdater(PeriodicBehaviour):
        """Periodically updates TR list."""
        async def run(self):
            # Filter TR data before copying
            tr_list_tmp = {k: TransportRobotAgent.filter(
                v.__dict__) for k, v in self.agent.tr_list.items()}
            tr_list_copy = deepcopy(tr_list_tmp)
            self.agent.update_view_model.emit(tr_list_copy, None, None)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Orders
        self.unused_id = 1  # Currently unused Order ID
        self.orders = {}
        self.order_factory = OrderFactory()
        self.order_behav = None

        # Callbacks used for updating GUI.
        self.update_tr_position = None
        self.update_view_model = None

        # GoM IDs start with 1, so that 0 can be used as set-aside's ID
        self.gom_count = 12

        # Maps JID to Point
        self.factory_map = {
            '': Point(x=-128.0, y=0.0)
        }
        self.tr_map = {}
        self.tr_list = {}

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
        self.position_handler = self.PositionHandler()
        self.position_updater = self.PositionUpdater(
            settings.TR_POSITION_UPDATE_PERIOD)
        self.tr_list_updater = self.TRListUpdater(
            settings.TR_LIST_UPDATE_PERIOD)

    async def setup(self):
        print(f"TickerAgent started at {datetime.datetime.now().time()}")
        if self.update_tr_position is None:
            raise Exception("update_tr_position not set")
        if self.update_view_model is None:
            raise Exception("update_view_model not set")

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

        inf_temp = Template()
        inf_temp.metadata = {"performative": "inform"}
        manager_temp = Template()
        manager_temp.sender = self.manager_jid
        pos_temp = (inf_temp & ~manager_temp)
        self.add_behaviour(self.position_handler, pos_temp)

        self.add_behaviour(self.StartAgents())

    def set_update_callbacks(self, update_tr_pos_callback, update_view_model_callback) -> None:
        """
        Sets callbacks used for updating GUI.

        :param update_tr_pos_callback:
        :param update_view_model_callback:
        """

        self.update_tr_position = update_tr_pos_callback
        self.update_view_model = update_view_model_callback

    def prepare(self):
        """
        Generates positions and JIDs for GoMs and TRs

        :return:
        """
        per_col = 5
        spray_diameter = 10
        jids = []
        for i in range(self.gom_count):
            # Create JIDs
            gom_jid = f"{settings.AGENT_NAMES['gom_base']}{i + 1}@{settings.HOST}"
            tr_jid = f"{settings.AGENT_NAMES['tr_base']}{i + 1}@{settings.HOST}"
            jids.append((gom_jid, tr_jid))

            # Create GoM and TR positions
            y = (i % per_col) * 48 - 96
            x = int(i / per_col) * 64 - 32
            xo = random.gauss(0, spray_diameter)
            yo = random.gauss(0, spray_diameter)

            self.factory_map[gom_jid] = Point(x=float(x), y=float(y))
            self.tr_map[tr_jid] = Point(x=float(x + xo), y=float(y + yo))

        return jids

    def perform_view_model_update(self):
        # Filter TR data before copying
        tr_list_tmp = {k: TransportRobotAgent.filter(
            v.__dict__) for k, v in self.tr_list.items()}
        tr_list_copy = deepcopy(tr_list_tmp)

        tr_map_copy = deepcopy(self.tr_map)
        factory_map_copy = deepcopy(self.factory_map)

        # Note that each param can be None. In that case it won't be updated.
        self.update_view_model.emit(
            tr_list_copy, tr_map_copy, factory_map_copy)


class Manager(Agent):
    class MainLoop(CyclicBehaviour):
        """
        Main agent loop. Takes an order from the queue, if available, updates its state and sends a request to a GoM.
        """

        async def on_start(self):
            print("Starting main loop . . .")

        async def run(self):
            while not self.agent.orders or not self.agent.free_goms:  # service an order if possible
                await sleep(settings.MANAGER_LOOP_TIMEOUT)
            # select a free gom to pass an order to
            gom: GoMInfo = random.choice(list(self.agent.free_goms.values()))
            self.agent.free_goms.pop(gom.jid)

            order: Order = heappop(self.agent.orders)
            oid = str(order.order_id)
            if oid not in self.agent.active_orders:
                self.agent.active_orders[oid] = ActiveOrder(order, '')
            payload = GoMOrder.create(
                order, self.agent.active_orders[oid].location)
            msg = Message(to=gom.jid)
            msg.set_metadata("performative", "request")
            msg.body = payload.to_json()
            msg.thread = oid
            print(f'Manager sent: {msg}')
            await self.send(msg)

        async def on_end(self):
            print(f"{self.agent} finished main loop with exit code {self.exit_code}.")

    class OrderRequestHandler(CyclicBehaviour):
        """Request from factory"""

        async def run(self):
            msg = await self.receive(timeout=settings.RECEIVE_TIMEOUT)
            if msg is None:
                return
            order = Order.from_json(msg.body)
            heappush(self.agent.orders, order)
            reply = Message(self.agent.factory_jid)
            reply.set_metadata("performative", "agree")
            await self.send(reply)

    class OrderRefuseHandler(CyclicBehaviour):
        """Refuse from GoM"""

        async def run(self):
            msg = await self.receive(timeout=settings.RECEIVE_TIMEOUT)
            if msg is None:
                return
            gom: GoMInfo = self.agent.gom_infos[str(msg.sender)]
            oid = msg.thread
            active_order: ActiveOrder = self.agent.active_orders[oid]
            heappush(self.agent.orders, active_order.order)
            print(f'{gom.jid} refused to process order{oid}.')
            raise UserWarning

    class OrderAgreeHandler(CyclicBehaviour):
        """Agree from GoM"""

        async def run(self):
            msg = await self.receive(timeout=settings.RECEIVE_TIMEOUT)
            if msg is None:
                return
            gom: GoMInfo = self.agent.gom_infos[str(msg.sender)]
            print(f'Agree received for order {msg.thread} from {msg.sender}.')

    class OrderDoneHandler(CyclicBehaviour):
        """Inform from GoM"""

        async def run(self):
            msg = await self.receive(timeout=settings.RECEIVE_TIMEOUT)
            if msg is None:
                return
            gom: GoMInfo = self.agent.gom_infos[str(msg.sender)]
            self.agent.free_goms[gom.jid] = gom

            oid = msg.thread
            active_order: ActiveOrder = self.agent.active_orders[oid]
            active_order.advance(gom.jid)
            print(f'{msg.sender} has completed a stage of order{oid}.')
            if not active_order.order.is_done():
                heappush(self.agent.orders, active_order.order)
            else:
                self.agent.active_orders.pop(oid)
                report = Message(self.agent.factory_jid)
                report.set_metadata("performative", "inform")
                report.thread = oid
                print('It was the final stage.')
                await self.send(report)

    class MalfunctionHandler(CyclicBehaviour):
        """Failure from GoM"""

        async def run(self):
            msg = await self.receive(timeout=settings.RECEIVE_TIMEOUT)
            if msg is None:
                return
            key = str(msg.sender)
            if key == self.factory_jid:
                print('Failure notice received from the factory.')
                raise UserWarning
            gom: GoMInfo = self.agent.gom_infos[key]
            print('Received malfunction notice:')
            print(msg)

    def __init__(self, factory_jid: str, gom_infos, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.gom_infos: Dict[str, GoMInfo] = {}  # all goms
        self.free_goms: Dict[str, GoMInfo] = {}  # goms that can take an order
        for gom_jid, operations in gom_infos:
            gom = GoMInfo(jid=gom_jid, machines=[
                          Machine(operation=op) for op in operations])
            self.gom_infos[gom_jid] = gom
            self.free_goms[gom_jid] = gom
        self.orders: List[Order] = []  # all orders accepted from factory
        # orders currently in progress
        self.active_orders: Dict[str, Order] = {}
        self.factory_jid: str = factory_jid

        self.main_loop = self.MainLoop()
        self.req_handler = self.OrderRequestHandler()
        self.ref_handler = self.OrderRefuseHandler()
        self.agr_handler = self.OrderAgreeHandler()
        self.done_handler = self.OrderDoneHandler()
        self.malfunction_handler = self.MalfunctionHandler()

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
        malfunction_temp = Template()
        malfunction_temp.metadata = {"performative": "failure"}
        self.add_behaviour(self.malfunction_handler, malfunction_temp)
        self.add_behaviour(self.main_loop)


class GroupOfMachinesAgent(Agent):
    def __init__(self, manager_jid, tr_jid, machines, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.manager_jid = manager_jid
        self.tr_jid = tr_jid
        self.machines = defaultdict(list)  # GoM's Machines collection
        for operation in machines:
            self.machines[operation].append(
                Machine(operation=operation, working=True))

        self.order = None  # current order
        # request message (from Manager) related to self.order
        self.msg_order = None

    class WorkBehaviour(OneShotBehaviour):
        """
        Perform work on current order.
        """

        async def run(self):
            assert self.agent.order is not None

            work_duration = settings.OP_DURATIONS[self.agent.order.operation]
            await asyncio.sleep(work_duration)

            # Reply to Manager with `inform`
            assert self.agent.msg_order is not None

            reply = self.agent.msg_order.make_reply()
            reply.set_metadata('performative', 'inform')
            await self.send(reply)

            # Set no active order
            self.agent.order = None
            self.agent.msg_order = None

    def can_accept_order(self, order):
        """
        Predicate that checks if TR can accept this order.

        :param order: requested order
        :return: result
        """

        if order.operation not in self.machines:
            return False

        return all([
            self.order is None,
            any(machine.working for machine in self.machines[order.operation])
        ])

    async def handle_tr_agree(self, msg, recv):
        """
        On `agree` message from `TR`.

        :param msg: received message
        :param recv: calling behaviour
        """

        assert msg is not None

    async def handle_tr_inform(self, msg, recv):
        """
        On `inform` message from `TR`

        :param msg: received message
        :param recv: calling behaviour
        """

        assert msg is not None
        self.add_behaviour(self.WorkBehaviour())

    async def handle_manager_request(self, msg, recv):
        """
        On `request` message from `Manager`

        :param msg: received message
        :param recv: calling behaviour
        """

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
                msg_tr = Message(to=self.tr_jid, body=msg.body)
                msg_tr.set_metadata('performative', 'request')
                await recv.send(msg_tr)

    async def setup(self):
        self.add_behaviour(
            behaviour=RecvBehaviour(self.handle_manager_request),
            template=Template(sender=self.manager_jid, metadata={
                              "performative": "request"})
        )
        self.add_behaviour(
            behaviour=RecvBehaviour(self.handle_tr_agree),
            template=Template(sender=self.tr_jid, metadata={
                              "performative": "agree"})
        )
        self.add_behaviour(
            behaviour=RecvBehaviour(self.handle_tr_inform),
            template=Template(sender=self.tr_jid, metadata={
                              "performative": "inform"})
        )


class LeaderBehaviour(FSMBehaviour):
    FIND_HELPERS_STATE = 'FIND_HELPERS_STATE'
    MOVE_SRC_STATE = 'MOVE_SRC_STATE'
    WAIT_FOR_HELPERS_SRC_STATE = 'WAIT_FOR_HELPERS_SRC_STATE'
    MOVE_DST_STATE = 'MOVE_DST_STATE'
    WAIT_FOR_HELPERS_DST_STATE = 'WAIT_FOR_HELPERS_DST_STATE'

    async def on_start(self):
        pass

    async def on_end(self):
        self.agent.idle = True

    def add_rec_transition(self, source, dest):
        self.add_transition(source=source, dest=source)
        self.add_transition(source=source, dest=dest)

    @classmethod
    def create(cls, agent):
        leader = cls()
        leader.add_state(name=cls.FIND_HELPERS_STATE,
                         state=FindHelpersState(), initial=True)

        src = agent.factory_map[agent.order.location]
        leader.add_state(name=cls.MOVE_SRC_STATE,
                         state=MoveState(name=cls.MOVE_SRC_STATE,
                                         next_state=cls.WAIT_FOR_HELPERS_SRC_STATE,
                                         destination=src))

        leader.add_state(name=cls.WAIT_FOR_HELPERS_SRC_STATE,
                         state=WaitForHelpersState(name=cls.WAIT_FOR_HELPERS_SRC_STATE,
                                                   next_state=cls.MOVE_DST_STATE,
                                                   home=False))

        dst = agent.factory_map[agent.gom_jid]
        leader.add_state(name=cls.MOVE_DST_STATE,
                         state=MoveState(name=cls.MOVE_DST_STATE,
                                         next_state=cls.WAIT_FOR_HELPERS_DST_STATE,
                                         destination=dst))

        leader.add_state(name=cls.WAIT_FOR_HELPERS_DST_STATE,
                         state=WaitForHelpersState(name=cls.WAIT_FOR_HELPERS_DST_STATE,
                                                   next_state=None,
                                                   home=True))

        leader.add_rec_transition(
            source=cls.FIND_HELPERS_STATE, dest=cls.MOVE_SRC_STATE)
        leader.add_rec_transition(
            source=cls.MOVE_SRC_STATE, dest=cls.WAIT_FOR_HELPERS_SRC_STATE)
        leader.add_rec_transition(
            source=cls.WAIT_FOR_HELPERS_SRC_STATE, dest=cls.MOVE_DST_STATE)
        leader.add_rec_transition(
            source=cls.MOVE_DST_STATE, dest=cls.WAIT_FOR_HELPERS_DST_STATE)

        return leader


class FindHelpersState(State):
    async def run(self):
        # TODO send and recive
        if len(self.agent.helpers) + 1 < self.agent.order.tr_count:
            self.set_next_state(LeaderBehaviour.FIND_HELPERS_STATE)
        else:
            self.set_next_state(LeaderBehaviour.MOVE_SRC_STATE)


class MoveState(State):
    def __init__(self, name, next_state, destination, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = name
        self.next_state = next_state
        self.destination = destination

    async def run(self):
        move_behaviour = self.agent.move(self.destination)
        await move_behaviour.join()
        self.set_next_state(self.next_state)
        

class WaitForHelpersState(State):
    def __init__(self, name, next_state, home, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = name
        self.next_state = next_state
        self.home = home

    async def run(self):
        pass


class TransportRobotAgent(Agent):
    def __init__(self, position, gom_jid, factory_jid, factory_map, tr_jids, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.idle = True
        self.position = position
        self.gom_jid = gom_jid
        self.factory_jid = factory_jid
        self.factory_map = factory_map
        self.tr_jids = tr_jids
        self.order = None  # from mother gom
        self.msg_order = None  # from mother gom
        self.loaded_order = None

        # TODO
        self.coworkers = ['tr-2@localhost']  # TODO: self.coworkers = []
        self.helping = {}

    # List of fields used when serializing.
    serialized_fields = ['coworkers', 'factory_jid', 'gom_jid',
                         'helping', 'idle', 'jid', 'loaded_order', 'order']

    def filter(d: dict) -> dict:
        """
        Filters a given dictionary by `serialized_fields`.

        :param d: TR converted to a dictionary.
        :return: Filtered dictionary.
        """
        return {k: v for (k, v) in d.items() if k in TransportRobotAgent.serialized_fields}

    class MoveBehaviour(PeriodicBehaviour):
        """
        Moves agent behaviour.
        """

        def __init__(self, destination, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.destination = destination
            self.tick_distance = settings.TR_SPEED * self.period.total_seconds()

        async def on_start(self):
            await asyncio.sleep(self.period.total_seconds())

        async def run(self):
            position = self.agent.position.to_array()
            vector = self.destination.to_array() - position
            remaining = np.linalg.norm(vector)
            if remaining <= self.tick_distance:
                self.agent.position = self.destination
                await self.after_tick()  # call after kill (after if)?
                self.kill()
            else:
                position += (self.tick_distance / remaining) * vector
                self.agent.position = Point.create(position)
                await self.after_tick()

        async def after_tick(self):
            """
            Method called after each tick
            """

            msg = Message(
                to=self.agent.factory_jid,
                body=self.agent.position.to_json()
            )
            msg.set_metadata("performative", "inform")
            await self.send(msg)

    class AfterBehaviour(OneShotBehaviour):
        """
        Behavior which triggers handler after the previous one has finished.

        :param wait_behaviour: first behaviour
        :param after_handler: Handler runs when a wait_behaviour is finished (takes one argument, calling behaviour).
        """

        def __init__(self, wait_behaviour, after_handler):
            super().__init__()
            self.wait_behaviour = wait_behaviour
            self.after_handler = after_handler

        async def run(self):
            await self.wait_behaviour.join()
            await self.after_handler(self)

    class DecideBehaviour(PeriodicBehaviour):
        def __init__(self, decide, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.decide = decide

        async def run(self):
            if self.agent.idle:
                self.agent.idle = self.decide()

    def move(self, destination):
        """
        Moves TR

        :param destination: location
        :return: move behaviour
        """

        move_behaviour = self.MoveBehaviour(
            destination, period=settings.TR_TICK_DURATION)
        self.add_behaviour(move_behaviour)
        return move_behaviour

    def add_after_behaviour(self, wait_behaviour, after_handler):
        """
        Add handler which triggers after a given behaviour.

        :param wait_behaviour: wait_for
        :param after_handler: Handler runs when a wait_behaviour is finished (takes one argument, calling behaviour).
        :return: after behaviour
        """

        after_behaviour = self.AfterBehaviour(wait_behaviour, after_handler)
        self.add_behaviour(after_behaviour)
        return after_behaviour

    async def load_order(self, behaviour):
        """
        Load an order (self.order).

        :param behaviour: calling behaviour
        """

        assert self.loaded_order is None
        assert self.msg_order is not None
        assert self.order is not None

        self.loaded_order = self.order
        destination = self.factory_map[self.gom_jid]
        move_behaviour = self.move(destination)
        self.add_after_behaviour(move_behaviour, self.deliver_order)

    async def deliver_order(self, behaviour):
        """
        Deliver an order (self.loaded) to GoM.

        :param behaviour: calling behaviour
        """

        assert self.loaded_order is not None
        assert self.msg_order is not None
        assert self.order is not None

        reply = self.msg_order.make_reply()
        reply.set_metadata('performative', 'inform')
        await behaviour.send(reply)
        self.loaded_order = None
        self.msg_order = None
        self.order = None
        self.idle = True

    def get_order(self):
        """
        Get an order (self.order) for GoM.
        """

        destination = self.factory_map[self.order.location]
        move_behaviour = self.move(destination)
        self.add_after_behaviour(move_behaviour, self.load_order)

    async def handle_gom_request(self, msg, recv):
        """
        On `request` message from `GoM`

        :param msg: received message
        :param recv: calling behaviour
        """

        assert self.msg_order is None
        assert self.order is None

        self.msg_order = msg
        self.order = GoMOrder.from_json(msg.body)
        reply = self.msg_order.make_reply()
        reply.set_metadata('performative', 'agree')
        await recv.send(reply)

    async def handle_tr_request(self, msg, recv):
        reply = msg.make_reply()
        order = GoMOrder.from_json(msg.body)
        if help(msg.sender, order):
            self.helping[msg.sender] = (order, msg, datetime.datetime.now())
            reply.set_metadata('performative', 'agree')
        else:
            reply.set_metadata('performative', 'refuse')
        await recv.send(reply)

    def help(self, sender, order):
        return True

    def decide(self):
        if self.order is not None:
            self.get_order()
            return False
        return True

    async def handle_tr_agree(self, msg, recv):
        pass

    async def handle_tr_refuse(self, msg, recv):
        pass

    async def handle_tr_inform(self, msg, recv):
        pass

    def tr_template(self, **kwargs):
        template_sum = None
        for tr_jid in self.tr_jids:
            template = Template(sender=tr_jid, **kwargs)
            if template_sum is None:
                template_sum = template
            else:
                template_sum = template_sum & template
        return template_sum

    async def setup(self):
        self.add_behaviour(
            behaviour=RecvBehaviour(self.handle_gom_request),
            template=Template(sender=self.gom_jid, metadata={
                              'performative': 'request'})
        )
        self.add_behaviour(
            behaviour=self.DecideBehaviour(
                self.decide, period=settings.TR_DECIDE_TIMEOUT)
        )

        # TR communication
        # self.add_behaviour(
        #    behaviour=RecvBehaviour(self.handle_tr_request),
        #    template=self.tr_template(metadata={'performative': 'request'})
        # )
        # self.add_behaviour(
        #    behaviour=RecvBehaviour(self.handle_tr_agree),
        #    template=self.tr_template(metadata={'performative': 'agree'})
        # )
        # self.add_behaviour(
        #    behaviour=RecvBehaviour(self.handle_tr_refuse),
        #    template=self.tr_template(metadata={'performative': 'refuse'})
        # )

        # self.add_behaviour(
        #    behaviour=RecvBehaviour(self.handle_tr_inform),
        #    template=self.tr_template(metadata={'performative': 'inform'})
        # )
