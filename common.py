from dataclasses import dataclass
from typing import List

from dataclasses_json import dataclass_json
from enums import Operation


@dataclass_json
@dataclass
class Order:
    priority: int  # N, 0 max
    order_id: int  # unique
    operations: List[Operation]
    current_operation: int  # index


@dataclass_json
@dataclass
class GoMOrder:
    priority: int  # N, 0 max
    order_id: int  # unique
    location: int  # 0 - warehouse, positive - socket_id
    operation: Operation
