from dataclasses import dataclass


@dataclass
class Event:
    event: str
    data: dict

    @staticmethod
    def from_dict(data: dict):
        return Event(data["event"], data["data"])
