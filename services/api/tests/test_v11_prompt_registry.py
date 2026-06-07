from __future__ import annotations

from app.tools.prompt_registry import list_prompts, load_prompt


def test_prompt_registry_lists_required_v11_prompts() -> None:
    prompts = {prompt["prompt_version"]: prompt for prompt in list_prompts()}

    for prompt_version in [
        "literature_answer_v1",
        "citation_support_v1",
        "metadata_extraction_v1",
        "bibtex_generation_v1",
    ]:
        assert prompt_version in prompts
        assert prompts[prompt_version]["char_count"] > 20

    loaded = load_prompt("literature_answer_v1")
    assert "source passages" in loaded["content"].lower()
