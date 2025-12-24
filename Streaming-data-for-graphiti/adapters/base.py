from abc import ABC, abstractmethod
from typing import Iterable
from schemas import StreamEvent

class BaseAdapter(ABC):
    @abstractmethod
    def parse(self, payload: dict) -> Iterable[StreamEvent]:
        pass
