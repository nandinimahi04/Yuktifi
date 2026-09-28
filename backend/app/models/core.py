"""Shared enums and helpers for all models."""
import enum
import uuid


def uid():
    return str(uuid.uuid4())


class AdminLevel(str, enum.Enum):
    village = "village"
    block = "block"
    district = "district"


class ConfidenceLevel(str, enum.Enum):
    high = "High"
    medium = "Medium"
    low = "Low"


class VerdictEnum(str, enum.Enum):
    GO = "GO"
    CAUTION = "CAUTION"
    ALTERNATIVE = "ALTERNATIVE"
    NOT_RECOMMENDED = "NOT_RECOMMENDED"
