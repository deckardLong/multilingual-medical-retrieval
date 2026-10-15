def pick_docs(ranked: list[tuple[str, float]], cfg) -> list[str]:
    """ranked: (uid, điểm doc) giảm dần. Giữ doc đầu bất kể ngưỡng, các doc sau phải đạt min_score
    và >= rel_drop × điểm doc đầu; tối đa max_docs."""
    if not ranked:
        return []
    top = ranked[0][1]
    kept = [ranked[0][0]]
    for uid, s in ranked[1:]:
        if len(kept) >= cfg.max_docs:
            break
        if cfg.min_score is not None and s < cfg.min_score:
            break
        if cfg.rel_drop is not None and s < cfg.rel_drop * top:
            break
        kept.append(uid)
    return kept[: cfg.max_docs]