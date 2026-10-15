from common.schema import Candidate


def group_by_uid(cands: list[Candidate]) -> dict[str, list[Candidate]]:
    """uid → các chunk của doc, điểm giảm dần; các doc cũng xếp theo điểm chunk tốt nhất giảm dần."""
    groups: dict[str, list[Candidate]] = {}
    for c in sorted(cands, key=lambda c: -c.score):
        groups.setdefault(c.uid, []).append(c)
    return groups