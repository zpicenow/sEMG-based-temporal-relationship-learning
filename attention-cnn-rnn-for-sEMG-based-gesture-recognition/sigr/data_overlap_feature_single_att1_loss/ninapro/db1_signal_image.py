from __future__ import division
from . import Dataset as Base


class Dataset(Base):

    name = 'ninapro-db1-signal'
    gestures = list(range(1, 53))
