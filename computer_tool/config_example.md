# Computer Tool 配置示例

## 环境变量配置 (.env文件)

请创建 `.env` 文件并配置以下环境变量：

```bash
# OpenAI API 配置 (推荐)
OPENAI_API_KEY=sk-your-openai-api-key-here

# 或者使用其他LLM服务 (可选)
ANTHROPIC_API_KEY=your-anthropic-api-key
GOOGLE_API_KEY=your-google-api-key  
DEEPSEEK_API_KEY=your-deepseek-api-key
AZURE_OPENAI_ENDPOINT=your-azure-endpoint
AZURE_OPENAI_KEY=your-azure-key

# Browser-Use 配置
DEFAULT_TEST_URL=https://www.baidu.com
BROWSER_NAME=chrome  # 可选: chrome, firefox, safari, edge
AUTO_LAUNCH_BROWSER=true

# Computer Tool 配置
ENABLE_CONSOLE_OUTPUT=true
ENABLE_FILE_LOGGING=false
MAX_RETRIES=3
TASK_TIMEOUT=60

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=computer_tool.log
```

## 快速配置步骤

1. **复制并重命名**
   ```bash
   cp config_example.md .env
   ```

2. **编辑 `.env` 文件**
   - 设置您的OpenAI API密钥
   - 根据需要调整其他配置

3. **验证配置**
   ```bash
   python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('API Key:', 'OK' if os.getenv('OPENAI_API_KEY') else 'Missing')"
   ```

## 注意事项

- `.env` 文件包含敏感信息，请勿提交到版本控制系统
- 确保API密钥有效且有足够的使用额度
- Browser-Use框架需要Python 3.11+