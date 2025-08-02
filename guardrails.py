# # guardrails.py

# import os
# from openai import AsyncOpenAI
# from pydantic import BaseModel, Field
# from typing import Literal

# from agents import Agent, Runner, OpenAIChatCompletionsModel, ModelSettings
# from agents.guardrail import input_guardrail, GuardrailFunctionOutput, InputGuardrailTripwireTriggered
# from agents.run_context import RunContextWrapper

# import config  # 引入您的配置文件

# # 1. 定义护栏分析结果的Pydantic模型，确保输出结构化
# class DisruptiveAnalysisResult(BaseModel):
#     """用于分析用户输入是否存在捣乱行为的模型。"""
#     is_disruptive: bool = Field(..., description="如果输入是捣乱行为（如脏话、指令注入、无关话题），则为True。")
#     reason: str = Field(..., description="判断输入是否为捣乱行为的简要理由。")
#     category: Literal["safe", "profanity", "prompt_injection", "off_topic"] = Field(..., description="将输入分类为'安全'、'脏话'、'指令注入'或'无关话题'。")

# # 2. 创建一个专门用于安全审查的轻量级Agent
# # 注意：这里我们使用异步客户端，因为SDK的护栏和Runner在内部是异步执行的
# security_screener_agent = Agent(
#     name="SecurityScreenerAgent",
#     instructions=config.GUARDRAIL_PROMPT,  # 我们将在config.py中添加这个新Prompt
#     model=OpenAIChatCompletionsModel(
#         model=config.SMALL_LLM_MODEL, # 使用您配置的小模型来做快速检查
#         openai_client=AsyncOpenAI(
#             api_key="ollama", 
#             base_url=config.OLLAMA_BASE_URL
#         ),
#     ),
#     model_settings=ModelSettings(
#         temperature=0.0, # 对于分类任务，使用低温度
#     ),
#     output_type=DisruptiveAnalysisResult, # 强制Agent输出我们定义的Pydantic模型
# )

# # 3. 定义输入护栏函数
# @input_guardrail
# async def disruptive_input_guardrail(
#     context: RunContextWrapper[None], 
#     agent: Agent, 
#     user_input: str
# ) -> GuardrailFunctionOutput:
#     """
#     一个智能输入护栏，使用LLM来检测用户的输入是否是捣乱行为。
#     """
#     print("🛡️ [护栏]: 启动智能输入护栏，分析用户输入...")
    
#     try:
#         # 运行安全审查Agent
#         result = await Runner.run(
#             starting_agent=security_screener_agent,
#             input=user_input
#         )
        
#         # 将Agent的输出转换为我们定义的Pydantic模型
#         analysis = result.final_output_as(DisruptiveAnalysisResult)

#         print(f"🛡️ [护栏]: 分析完成 -> 是否捣乱: {analysis.is_disruptive}, 理由: {analysis.reason}")

#         # 如果分析结果是捣乱，则触发护栏
#         return GuardrailFunctionOutput(
#             output_info={
#                 "is_disruptive": analysis.is_disruptive,
#                 "reason": analysis.reason,
#                 "category": analysis.category,
#             },
#             tripwire_triggered=analysis.is_disruptive
#         )
#     except Exception as e:
#         print(f"🛡️ [护栏]: 护栏Agent在执行时出错: {e}。为安全起见，默认放行。")
#         # 在护栏自身出错时，可以选择默认放行或阻止
#         return GuardrailFunctionOutput(
#             output_info={"error": str(e)},
#             tripwire_triggered=False
#         )