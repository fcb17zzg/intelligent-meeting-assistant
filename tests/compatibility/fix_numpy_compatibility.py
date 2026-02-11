"""
修复pyannote.audio的NumPy 2.0兼容性问题
"""
import os
import sys

print("="*60)
print("修复pyannote.audio的NumPy兼容性问题")
print("="*60)

# 找到inference.py文件
paths_to_try = [
    r"C:\Python312\Lib\site-packages\pyannote\audio\core\inference.py",
    os.path.join(sys.prefix, "Lib", "site-packages", "pyannote", "audio", "core", "inference.py"),
]

inference_file = None
for path in paths_to_try:
    if os.path.exists(path):
        inference_file = path
        print(f"✅ 找到文件: {inference_file}")
        break

if not inference_file:
    print("❌ 找不到inference.py文件，尝试搜索...")
    for root, dirs, files in os.walk(sys.prefix):
        if "inference.py" in files and "pyannote" in root and "audio" in root and "core" in root:
            inference_file = os.path.join(root, "inference.py")
            print(f"✅ 搜索到文件: {inference_file}")
            break

if not inference_file:
    print("❌ 无法找到inference.py文件")
    sys.exit(1)

# 备份
backup_file = inference_file + ".numpy_backup"
if not os.path.exists(backup_file):
    import shutil
    shutil.copy2(inference_file, backup_file)
    print(f"✅ 已备份到: {backup_file}")

# 读取文件内容
with open(inference_file, 'r', encoding='utf-8') as f:
    content = f.read()

# 修复np.NaN -> np.nan
old_code = 'np.NaN'
new_code = 'np.nan'

if old_code in content:
    count = content.count(old_code)
    content = content.replace(old_code, new_code)
    
    with open(inference_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ 修复成功！将 {count} 处 'np.NaN' 替换为 'np.nan'")
else:
    print("⚠️  未找到np.NaN，可能已经修复过")

# 检查是否还有其他NumPy 2.0兼容性问题
print("\n检查其他可能的NumPy 2.0问题...")

# 常见的NumPy 2.0变化
numpy_changes = {
    'np.float': 'np.float64',
    'np.int': 'np.int64', 
    'np.bool': 'np.bool_',
    'np.complex': 'np.complex128',
    'np.object': 'object',
    'np.str': 'str',
    'np.long': 'np.int64',
    'np.unicode': 'str',
}

lines = content.split('\n')
issues_found = []

for i, line in enumerate(lines):
    for old, new in numpy_changes.items():
        if old in line and f'import {old}' not in line:  # 避免修改导入语句
            issues_found.append((i+1, line.strip(), old, new))

if issues_found:
    print(f"⚠️  发现 {len(issues_found)} 处可能的NumPy 2.0兼容性问题:")
    for line_num, line_text, old, new in issues_found[:5]:  # 只显示前5个
        print(f"   第{line_num}行: '{old}' -> '{new}'")
        print(f"      {line_text}")
    
    fix_choice = input("\n是否自动修复这些问题？(y/n): ").lower()
    if fix_choice == 'y':
        # 重新读取文件
        with open(inference_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        for old, new in numpy_changes.items():
            if old in content:
                content = content.replace(old, new)
                print(f"  已修复: {old} -> {new}")
        
        with open(inference_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✅ 已修复所有发现的NumPy 2.0兼容性问题")
else:
    print("✅ 未发现其他明显的NumPy 2.0兼容性问题")

# 测试修复效果
print("\n" + "="*60)
print("测试修复效果")
print("="*60)

try:
    # 导入numpy检查版本
    import numpy as np
    print(f"NumPy版本: {np.__version__}")
    
    # 测试np.nan可用
    print(f"np.nan测试: {np.nan}")
    
    # 尝试导入pyannote
    import pyannote.audio
    print(f"✅ pyannote.audio导入成功，版本: {pyannote.audio.__version__}")
    
    # 尝试导入核心模块
    from pyannote.audio.core.inference import Inference
    print("✅ Inference导入成功")
    
    from pyannote.audio import Pipeline
    print("✅ Pipeline导入成功")
    
    print("\n🎉 NumPy兼容性问题修复成功！")
    
except Exception as e:
    print(f"❌ 测试失败: {e}")
    import traceback
    traceback.print_exc()
    
    # 提供更多帮助信息
    print("\n如果仍有问题，可以尝试:")
    print("1. 降级NumPy到1.x版本")
    print("2. 查看pyannote源代码中是否还有其他np.NaN引用")