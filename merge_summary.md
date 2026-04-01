此次合并主要更新了API配置和任务处理器的大纲保存逻辑，并新增了多个测试文件。API配置从n1n.ai切换到coding.st0722.top，模型从gpt-5.4-nano切换到Kimi-K2.5。任务处理器重构了大纲保存顺序和父子关系建立逻辑，提高了数据一致性。
| 文件 | 变更 |
|------|---------|
| backend/app/config.py | - 将API基础URL从https://api.n1n.ai/v1更改为https://coding.st0722.top/v1<br>- 更新了API密钥为sk-ivQlyYxtR5Q9Yiqyfzs5BPzWNqtlLd0sRrjp2KtVaG3Dhv6y<br>- 将模型名称从gpt-5.4-nano更改为Kimi-K2.5 |
| backend/app/services/task_processor.py | - 重构大纲保存顺序，按照世界纲→章纲→大纲→粗纲的顺序保存<br>- 优化大纲父子关系建立，直接在创建时设置parent_outline_id<br>- 改进章纲与粗纲的关联逻辑，通过chapter_range确定关联关系 |
| backend/tests/test_end_to_end_100_chapters.py | - 新增端到端测试文件，测试100章的完整流程 |
| backend/tests/test_full_workflow.py | - 新增完整工作流测试文件，测试整个系统流程 |
| backend/tests/test_llm_direct.py | - 新增直接LLM测试文件，测试LLM的直接调用 |
| backend/tests/test_openai_direct.py | - 新增直接OpenAI测试文件，测试OpenAI API的直接调用 |
| backend/tests/test_performance.py | - 新增性能测试文件，测试系统性能 |
| backend/tests/test_performance_simple.py | - 新增简单性能测试文件，测试基本性能指标 |
| backend/tests/test_real_novel_performance.py | - 新增真实小说性能测试文件，测试真实小说场景下的性能 |