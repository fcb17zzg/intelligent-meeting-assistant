"""
实体提取器
提取文本中的命名实体（人名、组织、时间等）
"""
import re
from typing import Dict, List, Optional, Any
from datetime import datetime
import dateparser


class EntityExtractor:
    """实体提取器"""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        
        # 中文姓名模式（简单版本）
        self.name_patterns = [
            r'([张李王赵刘陈杨黄周吴徐孙胡朱高林何郭马罗梁宋郑谢韩唐冯于董萧程曹袁邓许傅沈曾彭吕苏卢蒋蔡贾丁魏薛叶阎余潘杜戴夏钟汪田任姜范方石姚谭廖邹熊金陆郝孔白崔康毛邱秦江史顾侯邵孟龙万段漕钱汤尹黎易常武乔贺赖龚文])([伟芳娜秀英敏静丽强磊洋艳军杰娟涛明超秀兰霞平刚桂英])',
            r'([张李王赵刘陈杨黄周吴徐孙胡朱高林何郭马罗梁宋郑谢韩唐冯于董萧程曹袁邓许傅沈曾彭吕苏卢蒋蔡贾丁魏薛叶阎余潘杜戴夏钟汪田任姜范方石姚谭廖邹熊金陆郝孔白崔康毛邱秦江史顾侯邵孟龙万段漕钱汤尹黎易常武乔贺赖龚文])([总经理总监工师])',
        ]
        
        # 日期时间模式
        self.date_patterns = [
            r'(\d{4}年\d{1,2}月\d{1,2}日)',  # 2024年3月20日
            r'(\d{4}-\d{1,2}-\d{1,2})',      # 2024-03-20
            r'(\d{1,2}月\d{1,2}日)',         # 3月20日
            r'(本周[一二三四五六日])',        # 本周五
            r'(下周[一二三四五六日])',        # 下周一
            r'(下个月)',                      # 下个月
            r'(月底)',                        # 月底
            r'(Q[1-4])',                     # Q1, Q2, Q3, Q4
        ]
        
        # 组织机构模式
        self.organization_patterns = [
            r'([\u4e00-\u9fa5]+公司)',        # XX公司
            r'([\u4e00-\u9fa5]+部门)',        # XX部门
            r'([\u4e00-\u9fa5]+团队)',        # XX团队
            r'([\u4e00-\u9fa5]+组)',          # XX组
        ]
        
        # 时间表达式
        self.time_patterns = [
            r'(立刻|马上|尽快|立即|即刻)',    # 立即性
            r'([一二三四五六七八九十]+分钟[后内])',  # X分钟后
            r'([一二三四五六七八九十]+小时[后内])',  # X小时后
            r'([一二三四五六七八九十]+天[后内])',    # X天后
        ]
    
    def extract_names(self, text: str) -> List[str]:
        """提取人名"""
        names = []
        
        # 使用模式匹配
        for pattern in self.name_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                if isinstance(match, tuple):
                    name = ''.join(match)
                else:
                    name = match
                if name and name not in names:
                    names.append(name)
        
        # 简单规则：看起来像中文姓名（2-3个字符）
        words = re.findall(r'[\u4e00-\u9fa5]{2,3}', text)
        for word in words:
            # 排除常见非姓名词汇
            if word not in ['会议', '项目', '任务', '问题', '时间', '计划']:
                if word not in names:
                    names.append(word)
        
        return names
    
    def extract_dates(self, text: str) -> List[Dict[str, Any]]:
        """提取日期"""
        dates = []
        
        for pattern in self.date_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                date_text = match.group(0)
                
                # 尝试解析日期
                parsed_date = None
                try:
                    parsed_date = dateparser.parse(date_text, languages=['zh'])
                except:
                    pass
                
                dates.append({
                    'text': date_text,
                    'date': parsed_date,
                    'type': self._get_date_type(date_text),
                    'start': match.start(),
                    'end': match.end()
                })
        
        return dates
    
    def extract_organizations(self, text: str) -> List[str]:
        """提取组织机构"""
        organizations = []
        
        for pattern in self.organization_patterns:
            matches = re.findall(pattern, text)
            for org in matches:
                if org and org not in organizations:
                    organizations.append(org)
        
        return organizations
    
    def extract_time_expressions(self, text: str) -> List[Dict[str, Any]]:
        """提取时间表达式"""
        time_exprs = []
        
        for pattern in self.time_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                expr = match.group(0)
                time_exprs.append({
                    'text': expr,
                    'type': self._get_time_type(expr),
                    'start': match.start(),
                    'end': match.end()
                })
        
        return time_exprs
    
    def extract_all(self, text: str, include_confidence: bool = False) -> Dict[str, Any]:
        """提取所有实体"""
        entities = {
            'names': self.extract_names(text),
            'dates': self.extract_dates(text),
            'organizations': self.extract_organizations(text),
            'time_expressions': self.extract_time_expressions(text)
        }
        
        if include_confidence:
            # 添加置信度评分
            for key in entities:
                if isinstance(entities[key], list):
                    for i, entity in enumerate(entities[key]):
                        if isinstance(entity, dict):
                            entities[key][i]['confidence'] = self._calculate_confidence(entity)
                        else:
                            # 如果是字符串，转换为字典格式
                            entities[key][i] = {
                                'text': entity,
                                'confidence': self._calculate_confidence({'text': entity})
                            }
        
        return entities
    
    def extract_tasks_with_entities(self, text: str) -> List[Dict[str, Any]]:
        """提取带实体的任务"""
        tasks = []
        
        # 简单任务模式匹配
        task_patterns = [
            r'([\u4e00-\u9fa5]+)(负责|处理|完成|解决)([^。]+?)([，。；！？])',
            r'(需要|要|应该|必须)([^。]+?)(完成|解决|处理)([，。；！？])',
        ]
        
        for pattern in task_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                task_text = match.group(0)
                
                # 提取任务中的实体
                entities_in_task = self.extract_all(task_text)
                
                tasks.append({
                    'description': task_text,
                    'entities': entities_in_task,
                    'start': match.start(),
                    'end': match.end()
                })
        
        return tasks
    
    def _get_date_type(self, date_text: str) -> str:
        """获取日期类型"""
        if '年' in date_text or '-' in date_text:
            return 'absolute'
        elif '周' in date_text or '月' in date_text or '底' in date_text:
            return 'relative'
        elif date_text.startswith('Q'):
            return 'quarter'
        else:
            return 'unknown'
    
    def _get_time_type(self, time_text: str) -> str:
        """获取时间表达式类型"""
        if any(word in time_text for word in ['立刻', '马上', '尽快']):
            return 'immediate'
        elif '分钟' in time_text:
            return 'minutes'
        elif '小时' in time_text:
            return 'hours'
        elif '天' in time_text:
            return 'days'
        else:
            return 'relative'
    
    def _calculate_confidence(self, entity: Dict[str, Any]) -> float:
        """计算实体置信度"""
        text = entity.get('text', '')
        
        # 简单置信度计算
        confidence = 0.5  # 基础置信度
        
        # 根据类型调整
        if entity.get('type') == 'absolute':
            confidence += 0.3
        elif len(text) >= 3:
            confidence += 0.1
        
        # 限制在0-1之间
        return min(max(confidence, 0.0), 1.0)
    
    def _parse_relative_date(self, text: str) -> Optional[Dict[str, Any]]:
        """解析相对日期"""
        try:
            parsed = dateparser.parse(text, languages=['zh'])
            if parsed:
                return {
                    'text': text,
                    'date': parsed,
                    'type': 'relative'
                }
        except:
            pass
        
        return None