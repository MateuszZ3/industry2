import random
from heapq import heappush, heappop
import time
from dataclasses import dataclass
from typing import List

from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message
from spade.template import Template


@dataclass
class MachineInfo:
    state: bool
    operation: str


@dataclass
class GoMInfo:
    aid: str
    state: bool
    machines: List[MachineInfo]


@dataclass
class Order:  # todo jak to wysylac (ops po przecinku?)
    priority: int  # N, 0 max
    id: int
    operations: List[str]
    status: int  # def: -1 last_acc: i


@dataclass
class GoMOrder:
    priority: int
    operation: str


class Manager(Agent):
    class MainLoop(CyclicBehaviour):
        """main agent loop"""
        async def on_start(self):
            print("Starting main loop . . .")

        async def run(self):
            if not self.agent.goms:
                return
            gom: GoMInfo = random.choice(self.agent.goms)  # todo jak wybieramy?
            order: Order = heappop(self.agent.orders)
            self.agent.active_orders[order.id] = order
            msg = Message(gom.aid)
            msg.set_metadata("performative", "request")
            msg.thread = order.id
            msg.body = order.operations[order.status + 1]
            await self.send(msg)

        async def on_end(self):
            print(f"{self.agent} finished main loop with exit code {self.exit_code}.")


    class OrderRequestHandler(CyclicBehaviour):
        """request from factory"""
        async def run(self):  # todo cyc czy oneshot?
            msg = await self.receive()
            heappush(self.agent.orders, (1, msg))  # todo priorytet: thread? i jakas struktura info o zamowieniu: Order?
            reply = Message(self.agent.factory_aid)
            reply.set_metadata("performative", "agree")
            await self.send(reply)


    class OrderRefuseHandler(CyclicBehaviour):
        """refuse from GoM"""
        async def run(self):
            msg = await self.receive()
            oid = msg.thread
            order: Order = self.agent.active_orders[oid]
            heappush(self.agent.orders, order)
            self.agent.active_orders[oid] = None


    class OrderAgreeHandler(CyclicBehaviour):  # todo mozna zrobic nowy behavour z tym id, ale chyba przerost
        """agree from GoM"""
        async def run(self):
            msg = await self.receive()
            oid = msg.thread
            order: Order = self.agent.active_orders[oid]
            order.status += 1


    class OrderDoneHandler(CyclicBehaviour):
        """inform from GoM"""
        async def run(self):
            msg = await self.receive()
            oid = msg.thread
            order: Order = self.agent.active_orders[oid]
            heappush(self.agent.orders, order)
            self.agent.active_orders[oid] = None
            report = Message(self.agent.factory_aid)
            report.set_metadata("performative", "inform")
            await self.send(report)  # todo kiedy nie da sie wykonac?


    def __init__(self, jid, password, verify_security=False):
        super().__init__(jid, password, verify_security=False)
        self.goms = []  # todo tu dodać GoMy
        self.orders = []
        self.active_orders = {}  # todo potencjalnie jeden obiekt
        self.factory_aid = ''  # todo aid fabryki
        self.main_loop = self.MainLoop()
        self.req_handler = self.OrderRequestHandler()
        self.ref_handler = self.OrderRefuseHandler()
        self.agr_handler = self.OrderAgreeHandler()
        self.done_handler = self.OrderDoneHandler()

    async def setup(self):
        print("Manager starting . . .")
        fac_temp = Template()
        fac_temp.sender = self.factory_aid
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


if __name__ == "__main__":
    manager = Manager("agent@localhost", "pswd")
    future = manager.start()
    future.result()  # Wait until the start method is finished

    # wait until user interrupts with ctrl+C
    while not manager.main_loop.is_killed():
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            break
    manager.stop()
