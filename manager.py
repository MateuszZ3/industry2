import asyncio
import random
import time
from heapq import heappop, heappush

from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message
from spade.template import Template

from common import *
from settings import *


@dataclass
class MachineInfo:
    state: bool
    operation: str


@dataclass
class GoMInfo:
    aid: str
    state: bool
    machines: List[MachineInfo]


class Manager(Agent):
    class MainLoop(CyclicBehaviour):
        """Main agent loop"""
        async def on_start(self):
            print("Starting main loop . . .")

        async def run(self):
            if not self.agent.goms:
                await asyncio.sleep(MANAGER_LOOP_TIMEOUT)
                return
            gom: GoMInfo = random.choice(self.agent.goms)
            order: Order = heappop(self.agent.orders)
            last = self.agent.last_operation_location[
                order.order_id] if order.order_id in self.agent.last_operation_location else 0
            gorder = GoMOrder(order.priority, order.order_id, order.operations[order.current_operation], last)
            self.agent.active_orders[order.id] = order
            msg = Message(gom.aid)
            msg.set_metadata("performative", "request")
            msg.body = gorder.to_json()
            return
            msg.body = order.to_json()  # .from_json()
            msg.thread = order.id
            msg.body = order.operations[order.current_operation]
            await self.send(msg)

        async def on_end(self):
            print(f"{self.agent} finished main loop with exit code {self.exit_code}.")


    class OrderRequestHandler(CyclicBehaviour):
        """Request from factory"""
        async def run(self):
            msg = await self.receive(timeout=RECEIVE_TIMEOUT)
            order = Order.from_json(msg)
            print(order)
            heappush(self.agent.orders, order)
            reply = Message(self.agent.factory_aid)
            reply.set_metadata("performative", "agree")
            await self.send(reply)


    class OrderRefuseHandler(CyclicBehaviour):
        """Refuse from GoM"""
        async def run(self):
            msg = await self.receive(timeout=RECEIVE_TIMEOUT)
            oid = msg.thread  # todo
            order: Order = self.agent.active_orders[oid]
            heappush(self.agent.orders, order)
            self.agent.active_orders[oid] = None


    class OrderAgreeHandler(CyclicBehaviour):
        """Agree from GoM"""
        async def run(self):
            msg = await self.receive(timeout=RECEIVE_TIMEOUT)
            print('agree received for order ' + msg.thread)  # todo
            return
            oid = msg.thread
            order: Order = self.agent.active_orders[oid]


    class OrderDoneHandler(CyclicBehaviour):
        """Inform from GoM"""
        async def run(self):
            msg = await self.receive(timeout=RECEIVE_TIMEOUT)
            oid = msg.thread
            order: Order = self.agent.active_orders[oid]
            order.current_operation += 1
            self.agent.last_operation_location[oid] = msg.sender  # todo skąd nr
            heappush(self.agent.orders, order)
            self.agent.active_orders[oid] = None
            report = Message(self.agent.factory_aid)
            report.set_metadata("performative", "inform")
            report.thread = oid  # todo
            await self.send(report)


    def __init__(self, jid, password, verify_security=False):
        super().__init__(jid, password, verify_security=False)
        self.goms = []  # todo tu dodać GoMy
        self.orders = []
        self.active_orders = {}
        self.last_operation_location = {}
        self.factory_aid = 'todo'  # todo aid fabryki
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
