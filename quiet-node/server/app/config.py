import os


def _int(key: str, default: int) -> int:
    return int(os.environ.get(key, default))


def _float(key: str, default: float) -> float:
    return float(os.environ.get(key, default))


# Each is a property-style function so env changes in tests are respected.

def SYN_START(): return _int("SYN_START", 50000)
def COST_PER_REQUEST(): return _int("COST_PER_REQUEST", 10)
def COST_PER_KB(): return _int("COST_PER_KB", 1)
def REWARD_CLAIM(): return _int("REWARD_CLAIM", 25000)
def PENALTY_BAD_CLAIM(): return _int("PENALTY_BAD_CLAIM", 100)
def OPEN_INTERVAL_MIN_SECONDS(): return _float("OPEN_INTERVAL_MIN_SECONDS", 3600)
def OPEN_INTERVAL_MAX_SECONDS(): return _float("OPEN_INTERVAL_MAX_SECONDS", 14400)
def OPEN_DURATION_SECONDS(): return _float("OPEN_DURATION_SECONDS", 1.5)
def MAX_REQ_PER_MIN(): return _int("MAX_REQ_PER_MIN", 120)
def ENTROPY_MIN_KB(): return _int("ENTROPY_MIN_KB", 50)
def ENTROPY_MAX_KB(): return _int("ENTROPY_MAX_KB", 2048)
