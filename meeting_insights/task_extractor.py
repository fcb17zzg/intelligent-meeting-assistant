import re
from typing import List, Dict, Any
from datetime import datetime
import dateparser
from .models import ActionItem, Priority, Status

class TaskExtractor:
    """任务项提取器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.date_keywords = ['截止', 'deadline', '之前', '前完成', '下周一', '本周五']
        
    def extract_from_text(self, text: str, speaker_segments=None) -> List[ActionItem]:
        """从文本中提取任务项"""
        tasks = []
        
        # 方法1：规则匹配
        rule_based_tasks = self._extract_by_rules(text, speaker_segments)
        tasks.extend(rule_based_tasks)
        
        # 方法2：LLM提取（如果需要更复杂的识别）
        if self.config.get('use_llm_for_tasks', False):
            llm_tasks = self._extract_by_llm(text)
            tasks.extend(llm_tasks)
        
        # 去重和合并
        return self._deduplicate_tasks(tasks)
    
    def _extract_by_rules(self, text: str, speaker_segments=None) -> List[ActionItem]:
        """基于规则提取任务"""
        tasks = []
        
        # 常见任务模式的正则表达式
        patterns = [
            # 模式：某人负责某事在时间前
            r'([\u4e00-\u9fa5]+(?:经理|总|主管|同学)?)\s*(?:负责|跟进|处理)\s*([^，。；！？]+?)\s*(?:在|于|截止到|deadline)?\s*([\d年月日周一二三四五六天]+)',
            # 模式：需要做某事
            r'(?:需要|要|应该|必须)\s*(?:做|完成|处理|解决)\s*([^。；！？]+?(?:在|于|之前|之前完成))',
            # 模式：下次会议前完成某事
            r'([^。；！？]*?)\s*(?:下次会议|下周一|本周五|月底)\s*(?:前|之前)\s*(?:完成|提交|准备)',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                task_desc = match.group(0)
                assignee = match.group(1) if len(match.groups()) > 1 else None
                due_text = match.group(3) if len(match.groups()) > 2 else None
                
                # 解析日期
                due_date = None
                if due_text:
                    due_date = self._parse_date(due_text)
                
                # 确定优先级
                priority = self._determine_priority(task_desc)
                
                # 创建任务项
                task = ActionItem(
                    description=task_desc,
                    assignee=assignee,
                    due_date=due_date,
                    priority=priority,
                    confidence=0.7  # 规则提取的置信度
                )
                tasks.append(task)
        
        return tasks
    
    def _parse_date(self, date_text: str) -> Optional[datetime]:
        """解析中文日期文本"""
        try:
            # 使用dateparser处理中文日期
            parsed = dateparser.parse(date_text, languages=['zh'])
            return parsed
        except:
            return None
    
    def _determine_priority(self, task_desc: str) -> Priority:
        """根据任务描述确定优先级"""
        desc_lower = task_desc.lower()
        
        if any(word in desc_lower for word in ['紧急', '立刻', '马上', '尽快', '高优先级']):
            return Priority.HIGH
        elif any(word in desc_lower for word in ['重要', '关键', '优先']):
            return Priority.MEDIUM
        else:
            return Priority.LOW