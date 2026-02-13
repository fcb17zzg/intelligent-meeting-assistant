"""在报告生成器中添加决策显示"""

def add_decisions():
    filepath = 'src/visualization/report_generator.py'
    
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        new_lines.append(line)
        
        # 在关键主题后面添加决策部分
        if '## 关键主题' in line and i + 1 < len(lines):
            # 找到关键主题块的结束位置
            j = i + 1
            while j < len(lines) and '## ' not in lines[j]:
                j += 1
            
            # 在关键主题后面插入决策部分
            decisions_code = [
                '\n            # 会议决策\n',
                '            if \'decisions\' in insights and insights[\'decisions\']:\n',
                '                f.write("## 会议决策\\n\\n")\n',
                '                for decision in insights[\'decisions\']:\n',
                '                    f.write(f"- {decision}\\n")\n',
                '                f.write("\\n")\n',
                '\n'
            ]
            
            # 插入到关键主题块之后
            new_lines.extend(decisions_code)
            
        i += 1
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    
    print("✅ 已添加会议决策显示")
    print("  - 在报告中添加 '## 会议决策' 部分")

if __name__ == '__main__':
    add_decisions()