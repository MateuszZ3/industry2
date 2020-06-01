import json
import sys
from dataclasses import dataclass
from typing import List

from enums import Operation


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


def serialize(data, info=''):
    payload = {}
    for field in data.__dataclass_fields__.keys():
        payload[field] = getattr(data, field)
    return json.dumps({
        'class': type(data).__name__,
        'payload': payload,
        'info': info
    })

def deserialize(body):
    data = json.loads(body)
    current_module = sys.modules[__name__]
    instance = getattr(current_module, data['class'])(**data['payload'])
    return instance, data['info']
