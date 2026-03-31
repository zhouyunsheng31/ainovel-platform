import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "llm: 真实LLM冒烟测试（需API Key，手动触发 pytest -m llm）"
    )


@pytest.fixture(autouse=True)
def skip_llm_without_api_key(request):
    if request.node.get_closest_marker("llm"):
        api_key = os.environ.get("API_KEY") or os.environ.get("LLM_API_KEY")
        if not api_key:
            pytest.skip("LLM冒烟测试需要设置 API_KEY 或 LLM_API_KEY 环境变量")
