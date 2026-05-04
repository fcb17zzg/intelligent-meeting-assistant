import xml.etree.ElementTree as ET

file_path = 'paper/material/figures/ch3_usecases/fig3_1_user_module_usecase.drawio'
tree = ET.parse(file_path)
root = tree.getroot()

print("检查标签值...")
for cell in root.iter('mxCell'):
    cell_id = cell.get('id', '')
    if cell_id.startswith('20'):  # 标签 ID 为 201, 202 等
        value = cell.get('value', '')
        print(f"ID {cell_id}: {repr(value)}")
