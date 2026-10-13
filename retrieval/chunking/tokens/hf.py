# Define HF token counter schema

class HfTokenCounter:
    """Count by tokenizer of embedding model (tokenizer Rust, count by batch)."""

    def __init__(self, name: str):
        from transformers import AutoTokenizer
        self.tok = AutoTokenizer.from_pretrained(name, use_fast=True, model_max_length=10**9)

    def count(self, text: str) -> int:
        return len(self.tok.encode(text, add_special_tokens=False))

    def count_many(self, texts: list[str]) -> list[int]:
        if not texts:
            return []
        enc = self.tok(texts, add_special_tokens=False,
                       return_attention_mask=False, return_token_type_ids=False)
        return [len(ids) for ids in enc["input_ids"]]