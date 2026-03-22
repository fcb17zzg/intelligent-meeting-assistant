"""
任务项提取器
"""
import re
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import dateparser
from .models import ActionItem, Priority, Status

class TaskExtractor:
    """任务项提取器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.date_keywords = ['截止', 'deadline', '之前', '前完成', '下周一', '本周五']
        self.min_confidence = config.get('min_task_confidence', 0.6)

    def _normalize_task_text(self, text: str) -> str:
        cleaned = re.sub(r"\[\s*SPEAKER_[^\]]+\]\s*", "", str(text or ""), flags=re.IGNORECASE)
        cleaned = re.sub(r"\bSPEAKER_\d+\b", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s+", " ", cleaned).strip(" ，,。；;:：")
        cleaned = re.sub(r"^(好的|嗯|啊|然后|就是|这个|那个)\s*", "", cleaned)
        return cleaned

    def _is_reasonable_assignee(self, assignee: Optional[str]) -> bool:
        if not assignee:
            return False
        name = str(assignee).strip()
        if len(name) < 2 or len(name) > 8:
            return False
        blacklist = {
            "我们", "你们", "他们", "公司", "大家", "这个", "那个", "项目", "团队",
            "也是因为", "我不给你", "是怎么", "是怎麽", "没有给到", "给你自己", "是自己",
        }
        if name in blacklist:
            return False
        if any(marker in name for marker in ["因为", "怎么", "怎麽", "然后", "如果", "可以", "自己"]):
            return False
        if not re.fullmatch(r"[A-Za-z\u4e00-\u9fa5]{2,8}", name):
            return False
        return True

    def _build_task_description(self, pattern_index: int, match) -> str:
        if pattern_index == 0:
            owner = str(match.group(1) or "").strip()
            task = str(match.group(2) or "").strip()
            return f"{owner}负责{task}"
        if pattern_index == 1:
            task = str(match.group(1) or "").strip()
            due = str(match.group(2) or "").strip()
            return f"{task}（截止{due}）" if due else task
        if pattern_index == 2:
            owner = str(match.group(1) or "").strip()
            task = str(match.group(2) or "").strip()
            return f"{owner}负责{task}"
        if pattern_index == 3:
            return str(match.group(1) or "").strip()
        if pattern_index == 4:
            due = str(match.group(1) or "").strip()
            task = str(match.group(2) or "").strip()
            return f"{task}（截止{due}）" if due else task
        return str(match.group(0) or "").strip()
        
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
        
        # 置信度过滤
        tasks = [t for t in tasks if t.confidence >= self.min_confidence]
        
        # 去重和合并
        return self._deduplicate_tasks(tasks)
    
    def _extract_by_rules(self, text: str, speaker_segments=None) -> List[ActionItem]:
        """基于规则提取任务"""
        tasks = []
        
        # 改进的正则表达式模式
        patterns = [
            # 模式1: 某人负责某事
            r'([\u4e00-\u9fa5]{2,4})[，,\s]*(?:负责|跟进|处理|完成|做|解决|优化|开发)\s*([^，。；！？\n]{2,50})',
            # 模式2: 需要在时间前完成某事
            r'(?:需要|要|必须)[\s]*([^，。；！？\n]{2,50})[\s]*[在截至到]?[\s]*([\d年月日周一二三四五六天]+|下周一|本周五|月底|周五|下周三)[\s]*(?:前|之前|完成|提交|准备)',
            # 模式3: 任务指派
            r'([\u4e00-\u9fa5]{2,4})[，,\s]*(?:你|您)[\s]*([^，。；！？\n]{2,50})',
            # 模式4: 明确的任务描述
            r'(?:任务|todo|待办)[：:]\s*([^，。；！？\n]{2,50})',
            # 模式5: 截止日期在前
            r'([\d年月日周一二三四五六天]+|下周一|本周五|月底|周五|下周三)[\s]*(?:前|之前)[\s]*(?:完成|提交|准备)[\s]*([^，。；！？\n]{2,50})',
        ]
        
        for idx, pattern in enumerate(patterns):
            matches = re.finditer(pattern, text)
            for match in matches:
                task_desc = self._normalize_task_text(self._build_task_description(idx, match))
                if len(task_desc) < 6 or len(task_desc) > 80:
                    continue
                
                # 提取负责人
                assignee = None
                if idx in {0, 2} and len(match.groups()) >= 1 and match.group(1):
                    assignee = match.group(1)
                    if not self._is_reasonable_assignee(assignee):
                        assignee = None
                
                # 提取截止日期
                due_date = None
                due_text = None
                if idx in {1, 4} and len(match.groups()) >= 2:
                    due_text = match.group(2)
                    if idx == 4:
                        due_text = match.group(1)
                    if due_text and self.config.get('enable_date_parsing', True):
                        due_date = self._parse_date(due_text)
                
                # 确定优先级
                priority = self._determine_priority(task_desc)
                
                # 计算置信度
                confidence = self._calculate_confidence(match, due_text, assignee)
                
                # 创建任务项
                task = ActionItem(
                    description=task_desc,
                    assignee=assignee,
                    due_date=due_date,
                    priority=priority,
                    confidence=confidence,
                    status=Status.PENDING,
                    source_segment_ids=[],
                    context=None
                )
                tasks.append(task)
        
        return tasks
    
    def _parse_date(self, date_text: str) -> Optional[datetime]:
        """解析中文日期文本"""
        if not date_text:
            return None
        
        try:
            date_text = date_text.strip()
            
            # 处理特殊日期
            from datetime import datetime, timedelta
            today = datetime.now()
            
            # 本周五
            if date_text == "本周五":
                days_until_friday = (4 - today.weekday()) % 7
                if days_until_friday == 0:
                    days_until_friday = 7
                return today + timedelta(days=days_until_friday)
            
            # 下周三
            elif date_text == "下周三":
                days_until_wednesday = (2 - today.weekday()) % 7
                if days_until_wednesday <= 0:
                    days_until_wednesday += 7
                return today + timedelta(days=days_until_wednesday + 7)
            
            # 月底
            elif date_text == "月底":
                if today.month == 12:
                    return datetime(today.year + 1, 1, 1) - timedelta(days=1)
                else:
                    return datetime(today.year, today.month + 1, 1) - timedelta(days=1)
            
            # 周五
            elif date_text == "周五":
                days_until_friday = (4 - today.weekday()) % 7
                if days_until_friday == 0:
                    days_until_friday = 7
                return today + timedelta(days=days_until_friday)
            
            # 下周一
            elif date_text == "下周一":
                days_until_monday = (0 - today.weekday()) % 7
                if days_until_monday <= 0:
                    days_until_monday += 7
                return today + timedelta(days=days_until_monday + 7)
            
            # 使用dateparser处理其他中文日期
            parsed = dateparser.parse(date_text, languages=['zh'])
            return parsed
            
        except Exception as e:
            return None
    
    def _determine_priority(self, task_desc: str) -> Priority:
        """根据任务描述确定优先级"""
        desc_lower = task_desc.lower()
        
        # 高优先级关键词
        high_keywords = ['紧急', '立刻', '马上', '尽快', '高优先级', 'urgent', 'asap', 'immediately']
        # 中优先级关键词
        medium_keywords = ['重要', '关键', '优先', 'important', 'critical', 'priority']
        
        if any(word in desc_lower for word in high_keywords):
            return Priority.HIGH
        elif any(word in desc_lower for word in medium_keywords):
            return Priority.MEDIUM
        else:
            return Priority.LOW
    
    def _calculate_confidence(self, match, due_text: Optional[str], assignee: Optional[str]) -> float:
        """计算任务提取的置信度"""
        confidence = 0.7  # 基础置信度
        
        # 有明确负责人的提高置信度
        if assignee:
            confidence += 0.1
        
        # 有明确截止日期的提高置信度
        if due_text:
            confidence += 0.1
        
        # 任务描述长度的置信度
        desc = match.group(0)
        if len(desc) > 20:
            confidence += 0.05
        elif len(desc) < 10:
            confidence -= 0.1
        
        # 有明确任务动词的提高置信度
        task_verbs = ['负责', '跟进', '处理', '完成', '做', '解决', '优化', '开发']
        if any(verb in desc for verb in task_verbs):
            confidence += 0.05
        
        return min(confidence, 0.95)  # 不超过0.95
    
    def _deduplicate_tasks(self, tasks: List[ActionItem]) -> List[ActionItem]:
        """改进的任务去重，保留高置信度的"""
        task_dict = {}
        
        for task in tasks:
            # 使用标准化的描述作为键
            key = task.description.lower().strip()
            # 移除标点符号和空格
            key = re.sub(r'[，。！？、；:\s]', '', key)
            
            if key not in task_dict:
                task_dict[key] = task
            else:
                # 保留置信度更高的任务
                if task.confidence > task_dict[key].confidence:
                    task_dict[key] = task
        
        return list(task_dict.values())
    
    def _extract_by_llm(self, text: str) -> List[ActionItem]:
        """使用LLM提取任务（简化版）"""
        # 如果配置了LLM，这里可以实现调用LLM的逻辑
        # 当前版本返回空列表，由规则提取处理
        return []


__all__ = ['TaskExtractor']