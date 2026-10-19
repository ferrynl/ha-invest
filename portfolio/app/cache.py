"""Bounded in-memory cache; mutations and background updates invalidate it."""
import time
from threading import RLock

class StateCache:
    def __init__(self,ttl=30):
        self.ttl=ttl;self.lock=RLock();self.value=None;self.expires=0
    def invalidate(self):
        with self.lock:self.value=None;self.expires=0
    def get(self,loader):
        with self.lock:
            if self.value is None or time.monotonic()>=self.expires:
                self.value=loader();self.expires=time.monotonic()+self.ttl
            return self.value
