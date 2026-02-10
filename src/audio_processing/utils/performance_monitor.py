"""
性能监控工具
监控转录过程中的资源使用和性能指标
"""

import time
import psutil
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from collections import deque
import threading
import json

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """性能指标"""
    timestamp: float
    cpu_percent: float
    memory_mb: float
    gpu_memory_mb: Optional[float] = None
    disk_io_read_mb: float = 0
    disk_io_write_mb: float = 0
    network_sent_mb: float = 0
    network_recv_mb: float = 0


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self, update_interval: float = 1.0, max_history: int = 1000):
        """
        Args:
            update_interval: 更新间隔（秒）
            max_history: 最大历史记录数
        """
        self.update_interval = update_interval
        self.max_history = max_history
        
        self.metrics_history = deque(maxlen=max_history)
        self.is_monitoring = False
        self.monitor_thread = None
        
        # 初始IO计数
        self.last_disk_io = psutil.disk_io_counters()
        self.last_network_io = psutil.net_io_counters()
        self.last_update_time = time.time()
        
        logger.info(f"性能监控器初始化，更新间隔: {update_interval}s")
    
    def start_monitoring(self):
        """开始监控"""
        if self.is_monitoring:
            logger.warning("监控已在运行中")
            return
        
        self.is_monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
        
        logger.info("性能监控已启动")
    
    def stop_monitoring(self):
        """停止监控"""
        self.is_monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)
        
        logger.info("性能监控已停止")
    
    def _monitoring_loop(self):
        """监控循环"""
        while self.is_monitoring:
            try:
                self._collect_metrics()
                time.sleep(self.update_interval)
            except Exception as e:
                logger.error(f"收集性能指标失败: {e}")
                time.sleep(self.update_interval)
    
    def _collect_metrics(self):
        """收集性能指标"""
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=0.1)
            
            # 内存使用
            memory_info = psutil.Process().memory_info()
            memory_mb = memory_info.rss / (1024 * 1024)  # 转换为MB
            
            # 磁盘IO
            current_disk_io = psutil.disk_io_counters()
            disk_read_mb = (current_disk_io.read_bytes - self.last_disk_io.read_bytes) / (1024 * 1024)
            disk_write_mb = (current_disk_io.write_bytes - self.last_disk_io.write_bytes) / (1024 * 1024)
            
            # 网络IO
            current_network_io = psutil.net_io_counters()
            network_sent_mb = (current_network_io.bytes_sent - self.last_network_io.bytes_sent) / (1024 * 1024)
            network_recv_mb = (current_network_io.bytes_recv - self.last_network_io.bytes_recv) / (1024 * 1024)
            
            # GPU内存（如果可用）
            gpu_memory_mb = self._get_gpu_memory()
            
            # 创建指标对象
            metrics = PerformanceMetrics(
                timestamp=time.time(),
                cpu_percent=cpu_percent,
                memory_mb=memory_mb,
                gpu_memory_mb=gpu_memory_mb,
                disk_io_read_mb=disk_read_mb,
                disk_io_write_mb=disk_write_mb,
                network_sent_mb=network_sent_mb,
                network_recv_mb=network_recv_mb
            )
            
            # 保存到历史
            self.metrics_history.append(metrics)
            
            # 更新上一次的IO计数
            self.last_disk_io = current_disk_io
            self.last_network_io = current_network_io
            
        except Exception as e:
            logger.error(f"收集指标失败: {e}")
    
    def _get_gpu_memory(self) -> Optional[float]:
        """获取GPU内存使用"""
        try:
            import torch
            if torch.cuda.is_available():
                return torch.cuda.memory_allocated() / (1024 * 1024)  # MB
        except:
            pass
        
        try:
            import nvidia_smi
            nvidia_smi.nvmlInit()
            handle = nvidia_smi.nvmlDeviceGetHandleByIndex(0)
            info = nvidia_smi.nvmlDeviceGetMemoryInfo(handle)
            nvidia_smi.nvmlShutdown()
            return info.used / (1024 * 1024)  # MB
        except:
            pass
        
        return None
    
    def get_current_metrics(self) -> Optional[PerformanceMetrics]:
        """获取当前指标"""
        if self.metrics_history:
            return self.metrics_history[-1]
        return None
    
    def get_metrics_history(self, limit: Optional[int] = None) -> List[PerformanceMetrics]:
        """获取指标历史"""
        if limit:
            return list(self.metrics_history)[-limit:]
        return list(self.metrics_history)
    
    def get_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        if not self.metrics_history:
            return {}
        
        metrics_list = list(self.metrics_history)
        
        # 计算统计信息
        cpu_values = [m.cpu_percent for m in metrics_list]
        memory_values = [m.memory_mb for m in metrics_list]
        
        summary = {
            'total_samples': len(metrics_list),
            'duration_seconds': metrics_list[-1].timestamp - metrics_list[0].timestamp,
            'cpu_percent': {
                'avg': sum(cpu_values) / len(cpu_values),
                'max': max(cpu_values),
                'min': min(cpu_values)
            },
            'memory_mb': {
                'avg': sum(memory_values) / len(memory_values),
                'max': max(memory_values),
                'min': min(memory_values)
            }
        }
        
        # 如果有GPU数据
        gpu_values = [m.gpu_memory_mb for m in metrics_list if m.gpu_memory_mb is not None]
        if gpu_values:
            summary['gpu_memory_mb'] = {
                'avg': sum(gpu_values) / len(gpu_values),
                'max': max(gpu_values),
                'min': min(gpu_values)
            }
        
        return summary
    
    def save_report(self, filepath: str):
        """保存性能报告"""
        try:
            report = {
                'summary': self.get_summary(),
                'metrics': [
                    {
                        'timestamp': m.timestamp,
                        'cpu_percent': m.cpu_percent,
                        'memory_mb': m.memory_mb,
                        'gpu_memory_mb': m.gpu_memory_mb,
                        'disk_io_read_mb': m.disk_io_read_mb,
                        'disk_io_write_mb': m.disk_io_write_mb,
                        'network_sent_mb': m.network_sent_mb,
                        'network_recv_mb': m.network_recv_mb
                    }
                    for m in self.metrics_history
                ]
            }
            
            with open(filepath, 'w') as f:
                json.dump(report, f, indent=2)
            
            logger.info(f"性能报告保存到: {filepath}")
            
        except Exception as e:
            logger.error(f"保存性能报告失败: {e}")


# 全局监控器实例
_global_monitor = None

def get_global_monitor() -> PerformanceMonitor:
    """获取全局监控器实例"""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = PerformanceMonitor()
    return _global_monitor


def start_global_monitoring():
    """开始全局监控"""
    monitor = get_global_monitor()
    monitor.start_monitoring()


def stop_global_monitoring():
    """停止全局监控"""
    monitor = get_global_monitor()
    monitor.stop_monitoring()


def get_performance_summary() -> Dict[str, Any]:
    """获取性能摘要"""
    monitor = get_global_monitor()
    return monitor.get_summary()


# 使用示例
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("性能监控测试")
    print("="*50)
    
    # 创建监控器
    monitor = PerformanceMonitor(update_interval=0.5)
    
    # 开始监控
    monitor.start_monitoring()
    
    print("监控已启动，等待5秒收集数据...")
    time.sleep(5)
    
    # 停止监控
    monitor.stop_monitoring()
    
    # 获取摘要
    summary = monitor.get_summary()
    print(f"\n性能摘要:")
    print(f"  采样数: {summary.get('total_samples', 0)}")
    print(f"  监控时长: {summary.get('duration_seconds', 0):.1f}秒")
    
    if 'cpu_percent' in summary:
        cpu = summary['cpu_percent']
        print(f"  CPU使用率: 平均{cpu['avg']:.1f}%, 最大{cpu['max']:.1f}%")
    
    if 'memory_mb' in summary:
        mem = summary['memory_mb']
        print(f"  内存使用: 平均{mem['avg']:.1f}MB, 最大{mem['max']:.1f}MB")
    
    # 保存报告
    monitor.save_report("performance_report.json")
    print(f"\n性能报告已保存到: performance_report.json")