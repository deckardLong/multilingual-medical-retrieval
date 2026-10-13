# Count token approximately

import re

# Define tok regex
_TOK = re.compile(r"[\u4e00-\u9fff]|\w+|[^\w\s]")

# Schema
class ApproxTokenCounter:

    def count(self, text: str) -> int:
        return len(_TOK.findall(text))

    def count_many(self, texts: list[str]) -> list[int]:
        return [self.count(t) for t in texts]