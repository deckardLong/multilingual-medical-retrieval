from .base import TokenCounter
from .approx import ApproxTokenCounter

# Build counter
def build_counter(name: str) -> TokenCounter:
    if name == "approx":
        return ApproxTokenCounter()
    from .hf import HfTokenCounter
    return HfTokenCounter(name)

__all__ = ["TokenCounter", "ApproxTokenCounter", "build_counter"]