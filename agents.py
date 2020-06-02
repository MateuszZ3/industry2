import settings
import common
from collections import defaultdict
from enums import Operation
from dataclasses import dataclass
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message


@dataclass
class Machine:
    operation: Operation
    working: bool


class RecvBehaviour(CyclicBehaviour):
    def __init__(self, handler, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.handler = handler
    
    async def run(self):
        msg = await self.receive(timeout=settings.RECEIVE_TIMEOUT)
        if msg is not None:
            await self.handler(msg, self)


class GroupOfMachinesAgent(Agent):
    def __init__(self, manager_address, tr_address, machines, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.manager_address = manager_address
        self.tr_address = tr_address
        self.machines = defaultdict(list)
        for operation in machines:
            self.machines[operation].append(Machine(operation=operation, working=True))
        self.order = None
    
    def handle_info(self, info):
        if info:
            print(info)

    async def handle_manager_request(self, msg, recv):
        reply = msg.make_reply()
        order, info = common.deserialize(msg.body)
        self.handle_info(info)
        if self.order is None and order.operation in self.machines:
            self.order = order
            reply.set_metadata('performative', 'agree')
        else:
            reply.set_metadata('performative', 'refuse')
        await recv.send(reply)

    async def setup(self):
        self.add_behaviour(None)


class TransportRobotAgent(Agent):
    pass
