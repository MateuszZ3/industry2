from dataclasses import dataclass
from typing import List

from enums import *


@dataclass
class Order:
    priority: int  # N, 0 max
    id: int
    operations: List[Operation]
    status: int  # index of current operation


@dataclass
class GoMOrder:
    priority: int
    operation: Operation
