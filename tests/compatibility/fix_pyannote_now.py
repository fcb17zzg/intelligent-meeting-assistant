# 创建文件 fix_pyannote_now.py
import os
import sys

print("="*60)
print("修复pyannote.audio的set_audio_backend问题")
print("="*60)

# 尝试找到文件
paths_to_try = [
    r"C:\Python312\Lib\site-packages\pyannote\audio\core\io.py",
    os.path.join(sys.prefix, "Lib", "site-packages", "pyannote", "audio", "core", "io.py"),
]

io_file = None
for path in paths_to_try:
    if os.path.exists(path):
        io_file = path
        print(f"✅ 找到文件: {io_file}")
        break

if not io_file:
    print("❌ 找不到io.py文件，尝试搜索...")
    for root, dirs, files in os.walk(sys.prefix):
        if "io.py" in files and "pyannote" in root and "audio" in root and "core" in root:
            io_file = os.path.join(root, "io.py")
            print(f"✅ 搜索到文件: {io_file}")
            break

if not io_file:
    print("❌ 无法找到pyannote.audio的io.py文件")
    print("请手动查找并修改")
    sys.exit(1)

# 备份并修改文件
backup_file = io_file + ".backup"
if not os.path.exists(backup_file):
    import shutil
    shutil.copy2(io_file, backup_file)
    print(f"✅ 已备份到: {backup_file}")

# 读取文件内容
with open(io_file, 'r', encoding='utf-8') as f:
    content = f.read()

# 查找并替换
old_line = 'torchaudio.set_audio_backend("soundfile")'
new_line = '# torchaudio.set_audio_backend("soundfile")  # 已注释，新版本torchaudio不需要此设置'

if old_line in content:
    content = content.replace(old_line, new_line)
    
    # 写入修改后的内容
    with open(io_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ 文件修改成功！")
    print(f"  将 '{old_line}'")
    print(f"  替换为 '{new_line}'")
else:
    # 检查是否有变体
    lines = content.split('\n')
    modified = False
    for i in range(len(lines)):
        if 'set_audio_backend' in lines[i]:
            print(f"⚠️  找到类似行（第{i+1}行）: {lines[i].strip()}")
            lines[i] = '# ' + lines[i] + '  # 已注释'
            modified = True
    
    if modified:
        # 重新写入
        with open(io_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        print("✅ 已注释相关行")
    else:
        print("⚠️  未找到set_audio_backend调用，可能已经修复过了")

# 测试修复效果
print("\n" + "="*60)
print("测试修复效果")
print("="*60)

try:
    # 先导入torchaudio
    import torchaudio
    print(f"torchaudio版本: {torchaudio.__version__}")
    
    # 尝试导入pyannote
    import pyannote.audio
    print(f"pyannote.audio版本: {pyannote.audio.__version__}")
    
    # 尝试导入核心模块
    from pyannote.audio.core.io import AudioFile
    print("✅ AudioFile导入成功")
    
    from pyannote.audio import Pipeline
    print("✅ Pipeline导入成功")
    
    print("\n🎉 修复成功！现在可以正常使用pyannote.audio了")
    
except Exception as e:
    print(f"❌ 测试失败: {e}")
    import traceback
    traceback.print_exc()