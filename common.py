from dataclasses import dataclass
from typing import List

import numpy as np
from dataclasses_json import dataclass_json

from enums import Operation


@dataclass_json
@dataclass(order=True)
class Order:
    priority: int  # N, 0 max
    order_id: int  # unique
    operations: List[Operation]
    tr_counts: List[int]
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
    tr_count: int

    @classmethod
    def create(cls: type, order: Order, last: str):
        return cls(order.priority, order.order_id, last, order.operations[order.current_operation],
                   order.tr_counts[order.current_operation])


@dataclass_json
@dataclass
class Point:
    x: float
    y: float

    def to_array(self) -> np.array:
        return np.array((self.x, self.y))

    @classmethod
    def create(cls: type, point: np.array):
        return cls(point[0], point[1])


def clip(n, min_n, max_n):
    return min(max(n, min_n), max_n)
