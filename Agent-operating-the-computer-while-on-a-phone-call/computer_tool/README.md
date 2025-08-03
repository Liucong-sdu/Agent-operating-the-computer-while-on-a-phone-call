# 🌐 Computer Tool - Browser-Use 浏览器自动化系统

基于[Browser-Use](https://github.com/browser-use/browser-use)框架的语音控制浏览器自动化工具。该系统实现了语音指令到浏览器操作的完整链路，支持自然语言驱动的网页自动化任务。

## ✨ 主要特性

- 🎤 **语音指令处理**: 监听队列中的语音指令，支持实时处理
- 🤖 **AI驱动操作**: 基于Browser-Use框架，使用自然语言描述任务
- 🌐 **智能浏览器控制**: 自动打开测试网址，执行复杂网页操作
- 📊 **实时状态输出**: 详细的操作状态反馈和进度跟踪
- 🔄 **异步任务处理**: 高效的并发任务执行机制
- 🛠️ **模块化设计**: 清晰的组件分离，易于扩展和维护

## 🏗️ 系统架构

```
用户语音输入 → Voice Agent → Queue1 → Computer Tool → Browser-Use → 网页操作
     ↑                                      ↓              ↓
   语音反馈 ← 状态输出 ← Status Reporter ←  任务执行器 ←  操作结果
```

### 核心组件

1. **QueueProcessor** - 队列处理器：监听语音指令队列
2. **TaskExecutor** - 任务执行器：协调Browser-Use执行任务
3. **BrowserAgent** - Browser-Use代理：封装浏览器自动化功能
4. **StatusReporter** - 状态报告器：输出操作状态和结果
5. **WebLauncher** - 网页启动器：管理测试网址和浏览器会话

## 🚀 快速开始

### 1. 环境要求

- Python 3.11+
- Chrome/Firefox/Edge 浏览器
- OpenAI API密钥（推荐）或其他LLM API

### 2. 安装依赖

```bash
# 克隆项目
git clone <repository-url>
cd computer_tool

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 安装浏览器驱动（必需）
playwright install chromium --with-deps --no-shell
```

### 3. 配置环境变量

创建 `.env` 文件：

```bash
# OpenAI API 密钥（推荐）
OPENAI_API_KEY=sk-your-openai-api-key-here

# 或使用其他LLM
ANTHROPIC_API_KEY=your-anthropic-key
DEEPSEEK_API_KEY=your-deepseek-key

# 可选配置
DEFAULT_TEST_URL=https://www.baidu.com
BROWSER_NAME=chrome
```

### 4. 运行演示

```bash
# 运行完整演示
python computer_tool_demo.py

# 选择演示模式:
# 1. 自动演示 - 运行预设场景
# 2. 交互演示 - 手动输入指令
```

## 💻 使用方法

### 基础用法

```python
import asyncio
import queue
from computer_tool import create_queue_processor

# 创建语音指令队列
voice_queue = queue.Queue()

# 创建Computer Tool处理器
processor = create_queue_processor(
    queue1=voice_queue,
    test_url="https://www.baidu.com"
)

# 添加语音指令
voice_queue.put("在搜索框中输入'Python教程'")
voice_queue.put("点击搜索按钮")

# 启动处理
asyncio.run(processor.start_processing())
```

### 支持的指令类型

Browser-Use框架支持自然语言指令，例如：

- **导航操作**: "打开百度首页", "访问GitHub"
- **表单操作**: "在搜索框中输入'Python'", "点击登录按钮"
- **信息提取**: "获取页面标题", "查看第一个搜索结果"
- **复杂任务**: "搜索Python教程并打开第一个结果"

## 🔧 组件详解

### QueueProcessor - 队列处理器

负责监听和处理语音指令队列：

```python
from computer_tool import QueueProcessor

processor = QueueProcessor(
    input_queue=voice_queue,    # 语音指令队列
    output_queue=status_queue,  # 状态输出队列  
    test_url="https://example.com"
)
```

### BrowserAgent - Browser-Use代理

封装Browser-Use框架功能：

```python
from computer_tool import BrowserAgent

agent = BrowserAgent(
    api_key="your-api-key",
    model="gpt-4o-mini",  # 推荐使用
    temperature=0.7
)

# 执行浏览器任务
result = await agent.execute_web_task("打开百度并搜索Python")
```

### StatusReporter - 状态报告器

提供详细的状态输出：

```python
from computer_tool import StatusReporter

reporter = StatusReporter(
    enable_console_output=True,  # 控制台输出
    enable_file_logging=False    # 文件日志
)

# 报告任务状态
await reporter.report_success({
    "instruction": "搜索操作",
    "result": "搜索完成",
    "duration": 3.5
})
```

## 📁 项目结构

```
computer_tool/
├── __init__.py              # 模块初始化
├── queue_processor.py       # 队列处理器
├── task_executor.py         # 任务执行器
├── browser_agent.py         # Browser-Use代理
├── status_reporter.py       # 状态报告器
├── web_launcher.py          # 网页启动器
└── utils.py                 # 工具函数

computer_tool_demo.py        # 完整演示程序
requirements.txt             # 依赖列表
README.md                    # 项目说明
.env.example                 # 环境变量示例
```

## 🎯 演示场景

### 自动演示场景

系统会自动执行以下任务：

1. 自动打开测试网址
2. 在搜索框中输入"Python教程"
3. 点击搜索按钮
4. 查看搜索结果
5. 打开第一个结果
6. 返回上一页

### 交互演示

支持实时输入语音指令：

```
🎤 请输入语音指令: 打开GitHub
✅ 指令已发送: 打开GitHub
请等待浏览器操作完成...

🎤 请输入语音指令: 搜索browser-use项目
✅ 指令已发送: 搜索browser-use项目
请等待浏览器操作完成...
```

## ⚙️ 配置选项

### LLM模型选择

支持多种LLM模型：

- **GPT-4o-mini**: 性价比高，响应快速（推荐）
- **GPT-4o**: 最强性能，适合复杂任务
- **Claude-3.5-Sonnet**: 理解能力强
- **DeepSeek-V3**: 国产模型选择

### 浏览器配置

支持多种浏览器：

```python
# 指定浏览器
web_launcher = WebLauncher(browser_name="chrome")  # chrome, firefox, edge, safari
```

### 状态输出配置

```python
# 自定义状态输出
status_reporter = StatusReporter(
    enable_console_output=True,   # 控制台输出
    enable_file_logging=True,     # 文件日志
    max_history=100               # 历史记录数
)
```

## 🐛 故障排除

### 常见问题

1. **Browser-Use框架未安装**
   ```bash
   pip install browser-use
   ```

2. **浏览器驱动缺失**
   ```bash
   playwright install chromium --with-deps --no-shell
   ```

3. **API密钥未设置**
   - 检查 `.env` 文件中的API密钥配置
   - 确保密钥有效且有足够额度

4. **网络连接问题**
   - 确保测试网址可访问
   - 检查防火墙和代理设置

### 调试模式

启用详细日志输出：

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 🔮 未来规划

- [ ] 支持更多浏览器操作类型
- [ ] 增加错误恢复机制
- [ ] 实现任务调度和批处理
- [ ] 支持多标签页操作
- [ ] 增加可视化界面
- [ ] 支持更多LLM模型

## 🤝 贡献指南

欢迎贡献代码和建议！

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📄 许可证

本项目基于 MIT 许可证开源 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🙏 致谢

- [Browser-Use](https://github.com/browser-use/browser-use) - 强大的AI浏览器自动化框架
- [Playwright](https://playwright.dev/) - 现代化的浏览器自动化库
- [OpenAI](https://openai.com/) - 提供强大的语言模型API

---

**注意**: 这是Computer Tool项目的核心部分，专注于浏览器自动化功能。完整的Voice Agent + Computer Tool系统还需要语音识别和语音合成模块的集成。