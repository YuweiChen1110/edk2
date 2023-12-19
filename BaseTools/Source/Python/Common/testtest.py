from ctypeslib import parser
from ctypeslib.codegen import codegenerator
from ctypeslib import h2xml
from ctypeslib import hh_parser

# 使用 h2xml 工具将头文件转换为 XML
hfile = r'C:\Users\yuweiche\Code\Dev\edk2\YamlEnable\EmulationDfxVariable.h'
xml_output = r'C:\Users\yuweiche\Code\Dev\edk2\YamlEnable\output.xml'
h2xml(hfile, xml_output)

# 使用 ctypeslib2 进行解析
xml_data = open(xml_output).read()
header = hh_parser.parse_string(xml_data)
generator = codegenerator.LLVMCodeGenerator()
result = generator.parse(header)

# 打印生成的 ctypes 代码
print(result)

# with open(r'C:\Users\yuweiche\Code\YamlEnable\EmulationDfxVariable.h', 'r') as file:
#     code = file.read()

# parser = c_parser.CParser()
# ast = parser.parse(code)
