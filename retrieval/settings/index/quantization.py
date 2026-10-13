# Define quantization schema

from typing import Literal
from common.config import Cfg

# Define class
class QuantizationCfg(Cfg):
    enabled: bool
    kind: Literal["int8"]
    quantile: float
    always_ram: bool