"""
状态报告器 - Computer Tool核心组件
负责收集、格式化和输出浏览器操作的状态信息
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from queue import Queue
from enum import Enum


# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class StatusType(Enum):
    """状态类型枚举"""
    SYSTEM = "system"          # 系统状态
    TASK_STARTED = "task_started"     # 任务开始
    TASK_PROGRESS = "task_progress"   # 任务进度
    TASK_COMPLETED = "task_completed" # 任务完成
    TASK_FAILED = "task_failed"       # 任务失败
    ERROR = "error"            # 错误信息
    INFO = "info"              # 一般信息


class StatusReporter:
    """状态报告器 - 统一管理和输出操作状态"""
    
    def __init__(self, 
                 output_queue: Optional[Queue] = None,
                 enable_console_output: bool = True,
                 enable_file_logging: bool = False,
                 max_history: int = 100):
        """
        初始化状态报告器
        
        Args:
            output_queue: 输出队列（可选）
            enable_console_output: 是否启用控制台输出
            enable_file_logging: 是否启用文件日志
            max_history: 最大历史记录数
        """
        self.output_queue = output_queue
        self.enable_console_output = enable_console_output
        self.enable_file_logging = enable_file_logging
        self.max_history = max_history
        
        # 状态历史记录
        self.status_history: List[Dict[str, Any]] = []
        
        # 当前状态统计
        self.stats = {
            "total_tasks": 0,
            "successful_tasks": 0,
            "failed_tasks": 0,
            "start_time": datetime.now(),
            "last_activity": datetime.now()
        }
        
        logger.info("状态报告器初始化完成")
    
    async def report_status(self, status_info: Dict[str, Any]):
        """
        报告一般状态信息
        
        Args:
            status_info: 状态信息字典
        """
        status_data = self._format_status(status_info, StatusType.SYSTEM)
        await self._output_status(status_data)
    
    async def report_task_started(self, task_info: Dict[str, Any]):
        """
        报告任务开始状态
        
        Args:
            task_info: 任务信息
        """
        self.stats["total_tasks"] += 1
        
        status_data = self._format_status(task_info, StatusType.TASK_STARTED)
        status_data.update({
            "task_id": self.stats["total_tasks"],
            "message": f"开始执行任务: {task_info.get('instruction', '未知任务')}"
        })
        
        await self._output_status(status_data)
    
    async def report_progress(self, progress_info: Dict[str, Any]):
        """
        报告任务进度
        
        Args:
            progress_info: 进度信息
        """
        status_data = self._format_status(progress_info, StatusType.TASK_PROGRESS)
        await self._output_status(status_data)
    
    async def report_success(self, success_info: Dict[str, Any]):
        """
        报告任务成功完成
        
        Args:
            success_info: 成功信息
        """
        self.stats["successful_tasks"] += 1
        
        status_data = self._format_status(success_info, StatusType.TASK_COMPLETED)
        status_data.update({
            "success": True,
            "message": f"✅ 任务执行成功: {success_info.get('instruction', '未知任务')}",
            "duration": success_info.get('duration', 0),
            "result_summary": self._summarize_result(success_info.get('result', ''))
        })
        
        await self._output_status(status_data)
    
    async def report_error(self, error_title: str, error_detail: str, task_info: Dict[str, Any] = None):
        """
        报告错误信息
        
        Args:
            error_title: 错误标题
            error_detail: 错误详情
            task_info: 相关任务信息（可选）
        """
        self.stats["failed_tasks"] += 1
        
        error_data = {
            "error_title": error_title,
            "error_detail": error_detail,
            "task_info": task_info,
            "message": f"❌ {error_title}: {error_detail}"
        }
        
        status_data = self._format_status(error_data, StatusType.ERROR)
        await self._output_status(status_data)
    
    def _format_status(self, raw_data: Dict[str, Any], status_type: StatusType) -> Dict[str, Any]:
        """
        格式化状态数据
        
        Args:
            raw_data: 原始数据
            status_type: 状态类型
            
        Returns:
            格式化后的状态数据
        """
        formatted_data = {
            "timestamp": datetime.now().isoformat(),
            "status_type": status_type.value,
            "component": "computer_tool",
            **raw_data
        }
        
        # 更新最后活动时间
        self.stats["last_activity"] = datetime.now()
        
        return formatted_data
    
    async def _output_status(self, status_data: Dict[str, Any]):
        """
        输出状态数据到各个目标
        
        Args:
            status_data: 状态数据
        """
        # 添加到历史记录
        self._add_to_history(status_data)
        
        # 控制台输出
        if self.enable_console_output:
            self._console_output(status_data)
        
        # 队列输出
        if self.output_queue:
            try:
                self.output_queue.put_nowait(status_data)
            except Exception as e:
                logger.error(f"队列输出失败: {e}")
        
        # 文件日志输出
        if self.enable_file_logging:
            self._file_output(status_data)
    
    def _add_to_history(self, status_data: Dict[str, Any]):
        """添加到历史记录"""
        self.status_history.append(status_data)
        
        # 限制历史记录数量
        if len(self.status_history) > self.max_history:
            self.status_history.pop(0)
    
    def _console_output(self, status_data: Dict[str, Any]):
        """控制台输出"""
        timestamp = status_data.get("timestamp", "")[:19]  # 只取日期时间部分
        status_type = status_data.get("status_type", "").upper()
        message = status_data.get("message", "")
        
        # 根据状态类型选择不同的输出格式
        if status_type == "ERROR":
            print(f"[{timestamp}] 🔴 {status_type}: {message}")
        elif status_type == "TASK_COMPLETED":
            duration = status_data.get("duration", 0)
            print(f"[{timestamp}] ✅ {status_type}: {message} (耗时: {duration:.1f}秒)")
        elif status_type == "TASK_PROGRESS":
            progress = status_data.get("progress", 0)
            stage = status_data.get("stage", "")
            print(f"[{timestamp}] ⏳ {status_type}: [{progress}%] {stage} - {message}")
        else:
            print(f"[{timestamp}] ℹ️  {status_type}: {message}")
    
    def _file_output(self, status_data: Dict[str, Any]):
        """文件日志输出"""
        try:
            log_file = f"computer_tool_status_{datetime.now().strftime('%Y%m%d')}.log"
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(status_data, ensure_ascii=False) + '\n')
        except Exception as e:
            logger.error(f"文件日志写入失败: {e}")
    
    def _summarize_result(self, result: str, max_length: int = 200) -> str:
        """
        总结执行结果
        
        Args:
            result: 原始结果
            max_length: 最大长度
            
        Returns:
            总结后的结果
        """
        if not result:
            return "任务执行完成，无返回结果"
        
        result_str = str(result)
        if len(result_str) <= max_length:
            return result_str
        else:
            return result_str[:max_length] + "..."
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        total_time = (datetime.now() - self.stats["start_time"]).total_seconds()
        success_rate = (self.stats["successful_tasks"] / max(self.stats["total_tasks"], 1)) * 100
        
        return {
            "total_tasks": self.stats["total_tasks"],
            "successful_tasks": self.stats["successful_tasks"],
            "failed_tasks": self.stats["failed_tasks"],
            "success_rate": round(success_rate, 1),
            "total_runtime": round(total_time, 1),
            "start_time": self.stats["start_time"].isoformat(),
            "last_activity": self.stats["last_activity"].isoformat(),
            "status_history_count": len(self.status_history)
        }
    
    def get_recent_history(self, count: int = 10) -> List[Dict[str, Any]]:
        """获取最近的历史记录"""
        return self.status_history[-count:] if count > 0 else self.status_history
    
    async def generate_summary_report(self) -> Dict[str, Any]:
        """生成汇总报告"""
        stats = self.get_statistics()
        recent_history = self.get_recent_history(5)
        
        # 分析最近的任务情况
        recent_errors = [
            item for item in recent_history 
            if item.get("status_type") == "error" or item.get("status_type") == "task_failed"
        ]
        
        return {
            "report_type": "computer_tool_summary",
            "generated_at": datetime.now().isoformat(),
            "statistics": stats,
            "recent_activity": recent_history,
            "recent_errors": recent_errors,
            "system_status": "running" if self.stats["total_tasks"] > 0 else "idle",
            "recommendations": self._generate_recommendations(stats, recent_errors)
        }
    
    def _generate_recommendations(self, stats: Dict[str, Any], recent_errors: List[Dict[str, Any]]) -> List[str]:
        """生成建议信息"""
        recommendations = []
        
        success_rate = stats.get("success_rate", 0)
        if success_rate < 70:
            recommendations.append("任务成功率较低，建议检查网络连接和测试网址可访问性")
        
        if len(recent_errors) > 3:
            recommendations.append("最近错误频繁，建议检查Browser-Use框架配置和API密钥")
        
        if stats.get("total_tasks", 0) == 0:
            recommendations.append("尚未执行任何任务，可以尝试发送语音指令进行测试")
        
        if not recommendations:
            recommendations.append("系统运行正常，可以继续使用语音指令操作浏览器")
        
        return recommendations
    
    async def cleanup(self):
        """清理资源"""
        try:
            # 生成最终报告
            final_report = await self.generate_summary_report()
            
            if self.enable_console_output:
                print("\n" + "="*50)
                print("Computer Tool 运行汇总报告")
                print("="*50)
                print(f"总任务数: {final_report['statistics']['total_tasks']}")
                print(f"成功任务数: {final_report['statistics']['successful_tasks']}")
                print(f"失败任务数: {final_report['statistics']['failed_tasks']}")
                print(f"成功率: {final_report['statistics']['success_rate']}%")
                print(f"运行时长: {final_report['statistics']['total_runtime']}秒")
                print("="*50)
            
            logger.info("状态报告器清理完成")
            
        except Exception as e:
            logger.error(f"状态报告器清理出错: {e}")


def create_status_reporter(output_queue: Optional[Queue] = None,
                          enable_console: bool = True,
                          enable_file_log: bool = False) -> StatusReporter:
    """
    工厂函数：创建状态报告器
    
    Args:
        output_queue: 输出队列
        enable_console: 启用控制台输出
        enable_file_log: 启用文件日志
        
    Returns:
        状态报告器实例
    """
    return StatusReporter(
        output_queue=output_queue,
        enable_console_output=enable_console,
        enable_file_logging=enable_file_log
    )


# 示例使用
if __name__ == "__main__":
    async def demo():
        # 创建状态报告器
        reporter = create_status_reporter(enable_console=True)
        
        # 模拟各种状态报告
        await reporter.report_status({
            "type": "system",
            "status": "started",
            "message": "Computer Tool启动完成"
        })
        
        await reporter.report_task_started({
            "instruction": "打开百度并搜索Python教程"
        })
        
        await reporter.report_progress({
            "stage": "executing",
            "message": "正在执行浏览器操作...",
            "progress": 50
        })
        
        await asyncio.sleep(1)
        
        await reporter.report_success({
            "instruction": "打开百度并搜索Python教程",
            "result": "成功打开百度首页并完成搜索操作",
            "duration": 3.5
        })
        
        # 模拟错误
        await reporter.report_error(
            "网络连接错误", 
            "无法访问目标网站，请检查网络连接"
        )
        
        # 获取统计信息
        stats = reporter.get_statistics()
        print(f"\n统计信息: {stats}")
        
        # 生成汇总报告
        summary = await reporter.generate_summary_report()
        print(f"\n汇总报告: {json.dumps(summary, ensure_ascii=False, indent=2)}")
        
        # 清理
        await reporter.cleanup()
    
    # 运行演示
    asyncio.run(demo())