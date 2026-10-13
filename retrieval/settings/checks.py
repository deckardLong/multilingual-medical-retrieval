# Cross check each file config

# Define query margin
QUERY_MARGIN = 64

# Check compat
def check_compat(chunk, embed, rerank, retrieve) -> None:
    errs = []
    need = chunk.max_tokens + (chunk.ctx_margin_tokens if chunk.contextual_prefix else 0)
    if need > embed.max_length:
        errs.append(f"chunk cần ~{need} token (kèm ctx) > embed.max_length = {embed.max_length}: sẽ bị cắt ngầm")
    if rerank.enabled and need + QUERY_MARGIN > rerank.max_length:
        errs.append(f"chunk + query cần ~{need + QUERY_MARGIN} token > rerank.max_length = {rerank.max_length}")
    if not rerank.enabled and retrieve.select.min_score is not None:
        errs.append("select.min_score chỉ có nghĩa với điểm rerank, nhưng rerank.enabled = false")
    if retrieve.search.k_pool < retrieve.select.max_docs:
        errs.append("search.k_pool phải >= select.max_docs")
    if retrieve.search.k_fuse > retrieve.search.k_dense + retrieve.search.k_sparse:
        errs.append("search.k_fuse lớn hơn tổng k_dense + k_sparse")
    if errs:
        raise ValueError("Cấu hình không tương thích:\n  - " + "\n  - ".join(errs))