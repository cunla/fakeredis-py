from fakeredis._helpers import Database


class TimeSeriesCommandsMixin:
    # TimeSeries commands
    def __init__(self, *args, **kwargs):
        self._db: Database

    # TS.ADD
    # TS.ALTER
    # TS.CREATE
    # TS.CREATERULE
    # TS.DECRBY
    # TS.DEL
    # TS.DELETERULE
    # TS.GET
    # TS.INCRBY
    # TS.INFO
    # TS.MADD
    # TS.MGET
    # TS.MRANGE
    # TS.MREVRANGE
    # TS.QUERYINDEX
    # TS.RANGE
    # TS.REVRANGE
    #