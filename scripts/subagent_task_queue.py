#!/usr/bin/env python3
"""
Subagent Task Queue Manager
拉斐爾無盡學習系統 - Subagent 任務佇列管理器
基於 asyncio 的多代理任務協調系統
"""

import asyncio
import json
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Optional, List, Callable, Any
from pathlib import Path
import os

# ============ 任務狀態枚舉 ============
class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

# ============ 任務資料類別 ============
@dataclass
class SubagentTask:
    task_id: str
    task_name: str
    task_description: str
    model: str = "deepseek"
    priority: int = 5  # 1-10, 1 最高
    status: TaskStatus = TaskStatus.PENDING
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[str] = None
    error: Optional[str] = None
    context_mode: str = "isolated"  # isolated 或 fork
    timeout_seconds: int = 300
    max_retries: int = 3
    retry_count: int = 0
    
    def to_dict(self):
        return asdict(self)

# ============ 任務佇列管理器 ============
class TaskQueueManager:
    """Subagent 任務佇列管理器"""
    
    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = storage_path or os.path.join(
            os.path.expanduser("~/.hermes"),
            "state", "subagent_tasks.json"
        )
        self.tasks: List[SubagentTask] = []
        self.completed_tasks: List[SubagentTask] = []
        self.active_tasks: List[SubagentTask] = []
        self._load_tasks()
    
    def _load_tasks(self):
        """從磁碟載入任務"""
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.tasks = [SubagentTask(**t) for t in data.get('tasks', [])]
            except Exception as e:
                print(f"載入任務失敗: {e}")
    
    def _save_tasks(self):
        """儲存任務到磁碟"""
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        try:
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'tasks': [t.to_dict() for t in self.tasks],
                    'last_updated': datetime.now().isoformat()
                }, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"儲存任務失敗: {e}")
    
    def add_task(self, task: SubagentTask) -> str:
        """新增任務"""
        self.tasks.append(task)
        self._save_tasks()
        return task.task_id
    
    def get_task(self, task_id: str) -> Optional[SubagentTask]:
        """取得任務"""
        for task in self.tasks:
            if task.task_id == task_id:
                return task
        return None
    
    def update_task_status(self, task_id: str, status: TaskStatus, 
                          result: Optional[str] = None, error: Optional[str] = None):
        """更新任務狀態"""
        task = self.get_task(task_id)
        if task:
            task.status = status
            if status == TaskStatus.RUNNING and not task.started_at:
                task.started_at = datetime.now().isoformat()
            if status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                task.completed_at = datetime.now().isoformat()
            if result:
                task.result = result
            if error:
                task.error = error
            self._save_tasks()
    
    def get_pending_tasks(self) -> List[SubagentTask]:
        """取得待執行任務"""
        pending = [t for t in self.tasks if t.status == TaskStatus.PENDING]
        return sorted(pending, key=lambda x: x.priority)
    
    def get_stats(self) -> dict:
        """取得統計資訊"""
        return {
            'total': len(self.tasks),
            'pending': len([t for t in self.tasks if t.status == TaskStatus.PENDING]),
            'running': len([t for t in self.tasks if t.status == TaskStatus.RUNNING]),
            'completed': len([t for t in self.tasks if t.status == TaskStatus.COMPLETED]),
            'failed': len([t for t in self.tasks if t.status == TaskStatus.FAILED]),
        }
    
    def list_tasks(self, status_filter: Optional[TaskStatus] = None) -> List[SubagentTask]:
        """列出任務"""
        if status_filter:
            return [t for t in self.tasks if t.status == status_filter]
        return self.tasks
    
    def cancel_task(self, task_id: str) -> bool:
        """取消任務"""
        task = self.get_task(task_id)
        if task and task.status == TaskStatus.PENDING:
            task.status = TaskStatus.CANCELLED
            self._save_tasks()
            return True
        return False

# ============ Subagent 協調器 ============
class SubagentCoordinator:
    """Subagent 協調器 - 負責 spawn 和管理 subagent"""
    
    def __init__(self, task_queue: TaskQueueManager):
        self.task_queue = task_queue
        self._running = False
    
    async def execute_task(self, task: SubagentTask, 
                          executor_func: Callable) -> dict:
        """執行單一任務"""
        print(f"🔄 開始執行任務: {task.task_name}")
        self.task_queue.update_task_status(task.task_id, TaskStatus.RUNNING)
        
        start_time = time.time()
        try:
            # 這裡 executor_func 是實際執行任務的函數
            # 在真實情境中，這會呼叫 OpenClaw sessions_spawn
            result = await asyncio.wait_for(
                executor_func(task),
                timeout=task.timeout_seconds
            )
            
            elapsed = time.time() - start_time
            print(f"✅ 任務完成: {task.task_name} (耗時: {elapsed:.1f}s)")
            
            self.task_queue.update_task_status(
                task.task_id, 
                TaskStatus.COMPLETED,
                result=json.dumps(result, ensure_ascii=False)
            )
            return {'status': 'success', 'result': result, 'elapsed': elapsed}
            
        except asyncio.TimeoutError:
            print(f"⏰ 任務逾時: {task.task_name}")
            self.task_queue.update_task_status(
                task.task_id,
                TaskStatus.FAILED,
                error=f"任務執行逾時 ({task.timeout_seconds}s)"
            )
            return {'status': 'timeout', 'error': 'Task timeout'}
            
        except Exception as e:
            print(f"❌ 任務失敗: {task.task_name} - {str(e)}")
            self.task_queue.update_task_status(
                task.task_id,
                TaskStatus.FAILED,
                error=str(e)
            )
            return {'status': 'error', 'error': str(e)}
    
    async def run_task_queue(self, executor_func: Callable, 
                            max_concurrent: int = 3,
                            loop_interval: int = 5):
        """執行任務佇列（持續運行）"""
        self._running = True
        print(f"🚀 Subagent 協調器啟動 (最大並發: {max_concurrent})")
        
        while self._running:
            pending = self.task_queue.get_pending_tasks()
            running = [t for t in self.task_queue.tasks if t.status == TaskStatus.RUNNING]
            
            # 如果沒有達到最大並發，且有待執行任務
            available_slots = max_concurrent - len(running)
            if available_slots > 0 and pending:
                for task in pending[:available_slots]:
                    asyncio.create_task(self.execute_task(task, executor_func))
            
            await asyncio.sleep(loop_interval)
    
    def stop(self):
        """停止協調器"""
        self._running = False

# ============ 範例執行器 ============
async def example_executor(task: SubagentTask) -> dict:
    """範例任務執行器 - 模擬 subagent 工作"""
    print(f"  📋 Subagent 處理中: {task.task_description}")
    
    # 模擬工作負載
    await asyncio.sleep(min(task.timeout_seconds, 2))  # 最長2秒
    
    return {
        'task_id': task.task_id,
        'output': f"完成: {task.task_description[:50]}...",
        'model': task.model,
        'processed_at': datetime.now().isoformat()
    }

# ============ CLI 介面 ============
def main():
    import argparse
    parser = argparse.ArgumentParser(description="Subagent Task Queue Manager")
    subparsers = parser.add_subparsers(dest='command', help='命令')
    
    # 新增任務
    add_parser = subparsers.add_parser('add', help='新增任務')
    add_parser.add_argument('--name', '-n', required=True, help='任務名稱')
    add_parser.add_argument('--desc', '-d', required=True, help='任務描述')
    add_parser.add_argument('--model', '-m', default='deepseek', help='模型')
    add_parser.add_argument('--priority', '-p', type=int, default=5, help='優先級 1-10')
    
    # 列出任務
    list_parser = subparsers.add_parser('list', help='列出任務')
    list_parser.add_argument('--status', '-s', choices=['pending', 'running', 'completed', 'failed'], help='狀態篩選')
    
    # 顯示統計
    subparsers.add_parser('stats', help='顯示統計')
    
    # 執行佇列
    run_parser = subparsers.add_parser('run', help='執行任務佇列')
    run_parser.add_argument('--concurrent', '-c', type=int, default=3, help='最大並發數')
    
    args = parser.parse_args()
    
    queue = TaskQueueManager()
    coordinator = SubagentCoordinator(queue)
    
    if args.command == 'add':
        task_id = f"task_{int(time.time())}"
        task = SubagentTask(
            task_id=task_id,
            task_name=args.name,
            task_description=args.desc,
            model=args.model,
            priority=args.priority
        )
        queue.add_task(task)
        print(f"✅ 任務已新增: {task_id}")
        
    elif args.command == 'list':
        tasks = queue.list_tasks(TaskStatus[args.status.upper()] if args.status else None)
        print(f"\n📋 任務列表 (共 {len(tasks)} 個):")
        for t in tasks:
            print(f"  [{t.status.value}] {t.task_id} - {t.task_name}")
            
    elif args.command == 'stats':
        stats = queue.get_stats()
        print("\n📊 任務統計:")
        print(f"  總數: {stats['total']}")
        print(f"  待執行: {stats['pending']}")
        print(f"  執行中: {stats['running']}")
        print(f"  已完成: {stats['completed']}")
        print(f"  失敗: {stats['failed']}")
        
    elif args.command == 'run':
        print("啟動任務佇列執行器...")
        asyncio.run(coordinator.run_task_queue(example_executor, args.concurrent))
        
    else:
        parser.print_help()

if __name__ == "__main__":
    main()