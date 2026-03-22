"""
任务项提取器
"""
import re
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import dateparser
from .models import ActionItem, Priority, Status
from src.nlp_processing.llm_client import LLMClientFactory

class TaskExtractor:
    """任务项提取器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.date_keywords = ['截止', 'deadline', '之前', '前完成', '下周一', '本周五']
        self.min_confidence = config.get('min_task_confidence', 0.6)
        self.llm_client = None
        self.assignee_blacklist = {
            "我们", "你们", "他们", "公司", "大家", "这个", "那个", "项目", "团队", "部门",
            "也是因为", "我不给你", "是怎么", "是怎麽", "没有给到", "给你自己", "是自己", "有没有给",
            "月就必须", "天都重复", "公司就占", "题还是给", "其实", "虽然", "没有给你",
        }
        self.assignee_noise_markers = [
            "因为", "怎么", "怎麽", "然后", "如果", "可以", "自己", "有没有", "还是", "虽然", "必须",
            "就是", "现在", "那个", "这个", "没有给", "给你", "公司", "重复",
        ]
        self.description_noise_markers = [
            "的话", "就是", "然后", "你知道", "听一下", "有点", "比较", "这种", "那个", "这个",
            "也是因为", "没有给你", "有没有给", "题还是给", "公司就占", "天都重复", "月就必须",
        ]

        if self.config.get('use_llm_for_tasks', False):
            llm_config = self.config.get('llm') or {}
            if isinstance(llm_config, dict) and llm_config.get('provider') and llm_config.get('api_key'):
                try:
                    self.llm_client = LLMClientFactory.create_client(llm_config)
                except Exception:
                    self.llm_client = None

    def _normalize_task_text(self, text: str) -> str:
        cleaned = re.sub(r"\[\s*SPEAKER_[^\]]+\]\s*", "", str(text or ""), flags=re.IGNORECASE)
        cleaned = re.sub(r"\bSPEAKER_\d+\b", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s+", " ", cleaned).strip(" ，,。；;:：")
        cleaned = re.sub(r"^(好的|嗯|啊|然后|就是|这个|那个|所以|那就|其实)\s*", "", cleaned)
        return cleaned

    def _split_candidate_sentences(self, text: str) -> List[str]:
        parts = re.split(r"[。！？!?；;\n\r]+", str(text or ""))
        candidates: List[str] = []
        for part in parts:
            sentence = self._normalize_task_text(part)
            if not sentence:
                continue
            if "，" in sentence or "," in sentence:
                for chunk in re.split(r"[，,]+", sentence):
                    chunk = self._normalize_task_text(chunk)
                    if chunk:
                        candidates.append(chunk)
                continue
            # 超长句按逗号继续切分，降低 ASR 长句噪声污染。
            if len(sentence) > 80:
                for chunk in re.split(r"[，,]+", sentence):
                    chunk = self._normalize_task_text(chunk)
                    if chunk:
                        candidates.append(chunk)
            else:
                candidates.append(sentence)
        return candidates

    def _is_reasonable_task_description(self, description: str) -> bool:
        desc = self._normalize_task_text(description)
        if len(desc) < 6 or len(desc) > 80:
            return False
        if "SPEAKER_" in desc or "[" in desc or "]" in desc:
            return False
        if any(marker in desc for marker in self.description_noise_markers):
            return False
        if not re.search(r"(负责|完成|提交|跟进|处理|优化|安排|准备|解决|推进|落实|编写|整理)", desc):
            return False
        return True

    def _is_reasonable_assignee(self, assignee: Optional[str]) -> bool:
        if not assignee:
            return False
        name = str(assignee).strip()
        if len(name) < 2 or len(name) > 8:
            return False
        if name in self.assignee_blacklist:
            return False
        if any(marker in name for marker in self.assignee_noise_markers):
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
        if pattern_index == 5:
            owner = str(match.group(1) or "").strip()
            due = str(match.group(2) or "").strip()
            task = str(match.group(3) or "").strip()
            base = f"{owner}负责{task}" if owner else task
            return f"{base}（截止{due}）" if due else base
        return str(match.group(0) or "").strip()
        
    def extract_from_text(self, text: str, speaker_segments=None) -> List[ActionItem]:
        """从文本中提取任务项"""
        tasks = []
        extraction_mode = str(self.config.get('task_extraction_mode', 'hybrid') or 'hybrid').lower()

        # 方法1：模型提取（优先）
        if self.config.get('use_llm_for_tasks', False):
            llm_tasks = self._extract_by_llm(text)
            tasks.extend(llm_tasks)

            if llm_tasks and extraction_mode in {'llm_first', 'llm_only'}:
                tasks = [t for t in tasks if t.confidence >= self.min_confidence]
                return self._deduplicate_tasks(tasks)

            if extraction_mode == 'llm_only':
                return []

        # 方法2：规则匹配兜底
        rule_based_tasks = self._extract_by_rules(text, speaker_segments)
        tasks.extend(rule_based_tasks)
        
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
            r'^(?:请|由|让)?\s*([\u4e00-\u9fa5]{2,4})(?:同学|老师|经理|总)?(?=[，,\s]*(?:负责|跟进|处理|完成|做|解决|优化|开发|推进|落实|编写|整理))[，,\s]*(?:负责|跟进|处理|完成|做|解决|优化|开发|推进|落实|编写|整理)\s*([^，。；！？\n]{2,50})(?:[，,].*)?$',
            # 模式2: 需要在时间前完成某事
            r'^(?:[\u4e00-\u9fa5A-Za-z]{0,8})?(?:需要|要|必须|请)\s*([^，。；！？\n]{2,50}?)(?:在|于|截止)?\s*([\d年月日周一二三四五六天]+|下周一|本周[一二三四五六日天]|月底|月末|周[一二三四五六日天]|下周[一二三四五六日天]|今天|明天|后天)[\s]*(?:前|之前|完成|提交|准备|上线).*$',
            # 模式3: 任务指派
            r'^([\u4e00-\u9fa5]{2,4})(?=[，,\s]*(?:你|您)[\s]*(?:负责|跟进|处理|完成|推进|落实))[，,\s]*(?:你|您)[\s]*(?:负责|跟进|处理|完成|推进|落实)\s*([^，。；！？\n]{2,50})(?:[，,].*)?$',
            # 模式4: 明确的任务描述
            r'^(?:任务|todo|待办)[：:]\s*([^，。；！？\n]{2,50})$',
            # 模式5: 截止日期在前
            r'^([\d年月日周一二三四五六天]+|下周一|本周[一二三四五六日天]|月底|月末|周[一二三四五六日天]|下周[一二三四五六日天]|今天|明天|后天)[\s]*(?:前|之前)[\s]*(?:完成|提交|准备|上线)[\s]*([^，。；！？\n]{2,50})$',
            # 模式6: 主体 + 时间 + 完成 + 任务
            r'^([\u4e00-\u9fa5A-Za-z]{2,8})(?:要|需|需要)?在\s*([\d年月日周一二三四五六天]+|下周一|本周[一二三四五六日天]|月底|月末|周[一二三四五六日天]|下周[一二三四五六日天]|今天|明天|后天)[\s]*(?:前|之前)?(?:完成|提交|准备|上线)\s*([^，。；！？\n]{2,50})$',
        ]

        candidates = self._split_candidate_sentences(text)
        for sentence in candidates:
            for idx, pattern in enumerate(patterns):
                matches = re.finditer(pattern, sentence)
                for match in matches:
                    task_desc = self._normalize_task_text(self._build_task_description(idx, match))
                    if not self._is_reasonable_task_description(task_desc):
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
                    if idx in {1, 4, 5}:
                        if idx == 1 and len(match.groups()) >= 2:
                            due_text = match.group(2)
                        if idx == 4 and len(match.groups()) >= 1:
                            due_text = match.group(1)
                        if idx == 5 and len(match.groups()) >= 2:
                            due_text = match.group(2)
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
        """使用LLM提取任务（模型优先，规则兜底）。"""
        if not self.llm_client:
            return []

        prompt = f"""你是会议行动项抽取助手，请从以下会议文本中提取可执行任务。

会议文本：
{text}

抽取要求：
1) 仅提取明确可执行任务，忽略口语、寒暄、观点描述。
2) assignee 只保留真实负责人姓名；若无法确定，返回 null。
3) due_date 仅在文本有明确时间时填写，使用 ISO 8601 字符串；否则返回 null。
4) 每条任务包含 description、assignee、due_date、priority、confidence。
5) priority 只能是 low/medium/high。
6) confidence 为 0 到 1 的小数。

仅返回 JSON：
{{
  "action_items": [
    {{
      "description": "...",
      "assignee": "... 或 null",
      "due_date": "2026-03-27T18:00:00+08:00 或 null",
      "priority": "low|medium|high",
      "confidence": 0.88
    }}
  ]
}}"""

        try:
            result = self.llm_client.generate_json(prompt, temperature=0.1, max_tokens=1200)
        except Exception:
            return []

        raw_items = result.get("action_items", []) if isinstance(result, dict) else []
        if not isinstance(raw_items, list):
            return []

        items: List[ActionItem] = []
        for raw in raw_items:
            if not isinstance(raw, dict):
                continue

            description = self._normalize_task_text(str(raw.get("description", "") or ""))
            if not self._is_reasonable_task_description(description):
                continue

            assignee = raw.get("assignee")
            assignee = self._normalize_task_text(str(assignee or "")) if assignee else None
            if assignee and not self._is_reasonable_assignee(assignee):
                assignee = None

            due_date_value = raw.get("due_date")
            due_date = None
            if isinstance(due_date_value, str) and due_date_value.strip():
                try:
                    due_date = datetime.fromisoformat(due_date_value.replace("Z", "+00:00"))
                except Exception:
                    due_date = self._parse_date(due_date_value)

            priority_raw = str(raw.get("priority", "medium") or "medium").lower()
            if priority_raw not in {"low", "medium", "high"}:
                priority_raw = "medium"
            priority = Priority(priority_raw)

            confidence_raw = raw.get("confidence", 0.8)
            try:
                confidence = float(confidence_raw)
            except Exception:
                confidence = 0.8
            confidence = max(0.0, min(1.0, confidence))

            items.append(
                ActionItem(
                    description=description,
                    assignee=assignee,
                    due_date=due_date,
                    priority=priority,
                    confidence=confidence,
                    status=Status.PENDING,
                    source_segment_ids=[],
                    context=None,
                )
            )

        return items


__all__ = ['TaskExtractor']