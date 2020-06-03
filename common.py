from dataclasses import dataclass
from typing import List

from dataclasses_json import dataclass_json

from enums import Operation


@dataclass_json
@dataclass(order=True)
class Order:
    priority: int  # N, 0 max
    order_id: int  # unique
    operations: List[Operation]
    current_operation: int  # index

    def is_done(self):
        return len(self.operations) <= self.current_operation


@dataclass_json
@dataclass
class GoMOrder:
    priority: int  # N, 0 max
    order_id: int  # unique
    location: str  # "" - warehouse, "address@host" - socket_id
    operation: Operation

    @classmethod
    def create(cls: type, order: Order, last: str):
        return cls(order.priority, order.order_id, last, order.operations[order.current_operation])


@dataclass
class Point:
    x: float
    y: float
