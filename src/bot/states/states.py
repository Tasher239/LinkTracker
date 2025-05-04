from enum import Enum, auto


class TrackState(Enum):
    WAITING_FOR_LINK = auto()
    WAITING_FOR_CONFIRMATION = auto()
    WAITING_FOR_TAGS = auto()
    WAITING_FOR_FILTERS = auto()


class UnTrackState(Enum):
    WAITING_FOR_CHOICE = auto()
    WAITING_FOR_CONFIRMATION = auto()
