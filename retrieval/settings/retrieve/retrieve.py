# Define retrieve schema

from common.config import Cfg
from .decompose import DecomposeCfg
from .search import SearchCfg
from .select import SelectCfg

# Define class
class RetrieveCfg(Cfg):
    decompose: DecomposeCfg
    search: SearchCfg
    select: SelectCfg