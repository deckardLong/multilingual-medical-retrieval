# Context add in head of each chunk

# Make ctx
def make_ctx(contextual_prefix: bool, title: str, heading: str) -> str:
    if not contextual_prefix:
        return ""
    t, h = title.strip()
    heading.strip()
    return f"{t} | {h}" if h and h != t else t

# Embed text
def embed_text(ctx: str, text: str) -> str:
    return f"{ctx}\n{text}" if ctx else text