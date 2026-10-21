from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class Problem:
    level: Literal["error", "warning"]
    msg: str
    qid: int | None = None

    def __str__(self) -> str:
        where = f"[qid {self.qid}] " if self.qid is not None else ""
        return f"{self.level.upper():7} {where}{self.msg}"


@dataclass(frozen=True)
class Report:
    problems: tuple[Problem, ...]

    @property
    def errors(self) -> list[Problem]:
        return [p for p in self.problems if p.level == "error"]

    @property
    def warnings(self) -> list[Problem]:
        return [p for p in self.problems if p.level == "warning"]

    @property
    def ok(self) -> bool:
        return not self.errors

    def __str__(self) -> str:
        return "\n".join(str(p) for p in self.problems)


def sample(values, n: int = 5) -> str:
    """Rút gọn danh sách dài thành 'a, b, c … (+k)' để thông báo lỗi không dài hàng nghìn dòng."""
    vals = list(values)
    head = ", ".join(str(v) for v in vals[:n])
    return head + (f" … (+{len(vals) - n})" if len(vals) > n else "")