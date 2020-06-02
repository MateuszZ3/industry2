import asyncio
from collections import defaultdict
from dataclasses import dataclass

from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.behaviour import OneShotBehaviour, PeriodicBehaviour
from spade.message import Message
from spade.template import Template

import settings
from common import GoMOrder
from enums import Operation


@dataclass
class Machine:
    operation: Operation
    working: bool


class RecvBehaviour(CyclicBehaviour):
    def __init__(self, handler):
        super().__init__()
        self.handler = handler

    async def run(self):
        msg = await self.receive(timeout=settings.RECEIVE_TIMEOUT)
        if msg is not None:
            await self.handler(msg, self)


class GroupOfMachinesAgent(Agent):
    def __init__(self, socket_id, manager_address, tr_address, machines, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.socket_id = socket_id
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
            if self.socket_id == order.location:
                self.add_behaviour(self.WorkBehaviour())
            else:
                msg_tr = Message(to=self.tr_address)
                msg_tr.set_metadata('performative', 'request')
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
    def __init__(self, socket_id, position, gom_address, factory_map, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.socket_id = socket_id
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
        destination = self.factory_map[self.socket_id]
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
        self.add_after_behaviour(move_behaviour, self.loaded_order)

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
