import random
import time
from asyncio import sleep
from dataclasses import dataclass
from heapq import heappop, heappush
from typing import List

from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message
from spade.template import Template

import settings
from common import GoMOrder, Order


@dataclass
class MachineInfo:
    operation: str
    state: bool = True


@dataclass
class GoMInfo:
    jid: str
    machines: List[MachineInfo]


class Manager(Agent):
    class MainLoop(CyclicBehaviour):
        """Main agent loop"""
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
            last = self.agent.last_operation_location[
                order.order_id] if order.order_id in self.agent.last_operation_location else ''
            gorder = GoMOrder(order.priority, order.order_id, last, order.operations[order.current_operation])
            self.agent.active_orders[order.order_id] = order
            msg = Message(to=gom.jid)
            msg.set_metadata("performative", "request")
            msg.body = gorder.to_json()
            msg.thread = str(order.order_id)
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
            order: Order = self.agent.active_orders[oid]
            heappush(self.agent.orders, order)
            self.agent.active_orders[oid] = None

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
            order: Order = self.agent.active_orders[int(oid)]
            order.current_operation += 1
            self.agent.last_operation_location[oid] = msg.sender
            heappush(self.agent.orders, order)
            self.agent.active_orders[oid] = None
            report = Message(self.agent.factory_jid)
            report.set_metadata("performative", "inform")
            report.thread = oid
            await self.send(report)

    def __init__(self, factory_jid: str, gom_infos, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.gom_infos = []
        for gom_jid, operations in gom_infos:
            self.gom_infos.append(GoMInfo(jid=gom_jid, machines=[MachineInfo(operation=op) for op in operations]))
        self.orders = []
        self.active_orders = {}
        self.last_operation_location = {}
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


if __name__ == "__main__":
    manager = Manager(f"{settings.AGENT_NAMES['manager']}@{settings.HOST}", settings.PASSWORD)
    future = manager.start()
    future.result()  # Wait until the start method is finished

    # wait until user interrupts with ctrl+C
    while not manager.main_loop.is_killed():
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            break
    manager.stop()
