import yaml
import argparse
from FirmwareStorageFormat.Common import ModifyGuidFormat, struct2stream
from struct import pack, unpack
from Common.VariableAttributes import VariableAttributes
from AutoGen.GenVar import VariableMgr
from Common import StringUtils

STANDARD_SETTING = 'PcdsDynamicExHii.common.DEFAULT.STANDARD'
MANUFACTURING_SETTING = 'PcdsDynamicExHii.common.DEFAULT.MANUFACTURING'
YAML_DEFINE_DICT = 'defines'
YAML_SKU_DICT = 'sku'
YAML_DEFAULTSTORES_DICT = 'defaultstores'
YAML_VARIABLE_DICT = 'variable'

Arch_Dict = {'IA32', 'X64', 'Arm', 'common'}

def PACK_DELTA_DATA(skuid, defaultstorageid, delta_list):
    Buffer = bytearray()
    Buffer += pack("=L", 4+8+8)
    Buffer += pack("=Q", int(skuid))
    Buffer += pack("=Q", int(defaultstorageid))
    for (delta_offset, value) in delta_list:
        Buffer += pack("=L", delta_offset)
        Buffer = Buffer[:-1] + pack("=B", value)
    Buffer = pack("=L", len(Buffer) + 4) + Buffer
    return Buffer

def PACK_VARIABLE_HEADER(attribute, namesize, datasize, vendorguid):

    Buffer = pack('=H', 0x55AA) # pack StartID
    Buffer += pack('=B', 0x3F)  # pack State
    Buffer += pack('=B', 0)     # pack reserved
    Buffer += pack('=L', attribute)
    Buffer += pack('=L', namesize)
    Buffer += pack('=L', datasize)
    Buffer += vendorguid
    return Buffer

def sort_by_field_offset(item):
    return item[next(iter(item))]['field_offset']

class YamlVariable():
    def __init__(self, name='') -> None:
        self.Name = name
        self.VarName = ''
        self.VarPcdName = ''
        self.VarGuid = ''
        self.VarDefaultValue = 0
        self.VarAttribute = ''
        self.VarHeaderFile = ''

        self.VarAttr = 0x00000000
        self.VarProp = 0x00000000

        self.VarHeaderBuffer = b''
        self.VarNameBuffer = b''
        self.VarDefaultDataBuffer = b''
        self.VarDeltaDataBuffer = b''
        self.VarFieldList = []
        self.VarFieldDict = {}
        self.MacroDict = {}
        self.VarDefaultSetting = []
        self.VarCustomizedSetting = {}

    def GenVarHeaderBuffer(self):
        self.VarHeaderBuffer = PACK_VARIABLE_HEADER(self.VarAttr, len(StringUtils.StringToArray(self.VarName).split(",")), len(self.VarDefaultDataBuffer), self.VarGuid)

    def GenVarNameBuffer(self):
        self.VarNameBuffer = VariableMgr.PACK_VARIABLE_NAME(StringUtils.StringToArray(self.VarName))

    def GenVarDeltaDataBuffer(self, skuid, defaultstoreid):
        delta_fields_collection = sorted(self.VarCustomizedSetting[(skuid, defaultstoreid)], key=sort_by_field_offset)
        delta_data_set = []
        for item in delta_fields_collection:
            field_name = list(item.keys())[0]
            delta_data = [(item[field_name]['field_offset'], item[field_name]['field_default_value'])]
            delta_data_set.extend(delta_data)
        self.VarDeltaDataBuffer = VariableMgr.AlignData(PACK_DELTA_DATA(skuid, defaultstoreid, delta_data_set), 8)

    def GetVarAttrProp(self):
        if self.VarAttribute:
            self.VarAttr, self.VarProp = VariableAttributes.GetVarAttributes(self.VarAttribute)
        else:
            self.VarAttr = 0x07

    def GetVarGuid(self):
        self.VarGuid = struct2stream(ModifyGuidFormat(self.VarGuid))

    def CollectCustomizedField(self, skuid, defaultstoreid, field_lists):
        current_setting = []
        for field in field_lists:
            field_name = list(field.keys())[0]
            if field_name not in current_setting:
                new_field = {}
                new_field[field_name] = {}
                field_length = field[field_name]['length']
                field_length = self.GetFieldLengthFromMacro(field_length, field_name)
                field_value = field[field_name]['value']
                new_field[field_name]['field_length'] = field_length
                new_field[field_name]['field_default_value'] = field_value
                new_field[field_name]['field_offset'] = self.VarFieldDict[field_name][field_name]['field_offset']
                current_setting.append(new_field)
        self.VarCustomizedSetting[(skuid, defaultstoreid)] = current_setting
        self.GenVarDeltaDataBuffer(skuid, defaultstoreid)

    def CollectField(self, field_lists):
        cur_offset = 0
        for field in field_lists:
            field_name, field_length = self.AddNewField(field, cur_offset)
            cur_offset += int(field_length)
            field_buffer = hex(field[field_name]['value']) * field_length
            self.VarDefaultDataBuffer += field_buffer.encode('utf-8')
        self.VarDefaultSetting = self.VarFieldList

    def AddNewField(self, field, offset):
        field_name = list(field.keys())[0]
        if field_name not in self.VarFieldList:
            new_field = {}
            new_field[field_name] = {}
            field_length = field[field_name]['length']
            field_length = self.GetFieldLengthFromMacro(field_length, field_name)
            field_value = field[field_name]['value']
            new_field[field_name]['field_length'] = field_length
            new_field[field_name]['field_default_value'] = field_value
            new_field[field_name]['field_offset'] = offset
            self.VarFieldList.append(new_field)
            self.VarFieldDict[field_name] = new_field
        return field_name, field_length

    def GetFieldLengthFromMacro(self, field_length, field_name):
        if type(field_length) == str:
            if field_length.startswith('$'):
                field_length = field_length.replace('$(', '').replace(')', '')
            if field_length in self.MacroDict:
                field_length = self.MacroDict[field_length]
            else:
                raise 'Unknown Field Length: {}'.format(field_name)
        return field_length

    def GetVarDefaultBuffer(self):
        return self.VarHeaderBuffer + VariableMgr.AlignData(self.VarNameBuffer + self.VarDefaultDataBuffer)

class YamlConfig():
    def __init__(self, inputdata='') -> None:
        self.inputdata = inputdata
        self.define_dict = {}
        self.sku_dict = {}
        self.defaultstores_dict = {}
        self.variable_dict = {}
        self.standard_setting_config = {}
        self.customized_setting_config = {}
        self.variable_list = []

        self.VpdRegionSize = None
        self.nv_default_buffer = b''
        self.data_delta_structure_buffer = b''

    def ReadVariable(self, target_variable):
        target_variable_name = list(target_variable.keys())[0]
        var_content = target_variable[target_variable_name]
        yaml_var = YamlVariable(target_variable_name)
        yaml_var.MacroDict = self.define_dict
        for item in var_content:
            if 'Name' in item:
                yaml_var.VarName = item['Name']
                yaml_var.GenVarNameBuffer()
            if 'PcdName' in item:
                yaml_var.VarPcdName = item['PcdName']
            if 'Guid' in item:
                yaml_var.VarGuid = item['Guid']
                yaml_var.GetVarGuid()
            if 'DefaultValue' in item:
                yaml_var.VarDefaultValue = item['DefaultValue']
            if 'VarAttribute' in item:
                yaml_var.VarAttribute = item['VarAttribute']
            if 'HeaderFile' in item:
                yaml_var.VarHeaderFile = item['HeaderFile']
            yaml_var.GetVarAttrProp()
        return target_variable_name, yaml_var

    def CollectDefine(self):
        self.define_dict = self.inputdata[YAML_DEFINE_DICT]

    def CollectSku(self):
        self.sku_dict = self.inputdata[YAML_SKU_DICT]

    def CollectDefaultStores(self):
        self.defaultstores_dict = self.inputdata[YAML_DEFAULTSTORES_DICT]

    def CollectVariable(self):
        variable_dict = self.inputdata[YAML_VARIABLE_DICT]
        for item in variable_dict:
            cur_var_name, cur_var = self.ReadVariable(item)
            if cur_var_name not in self.variable_list:
                self.variable_list.append(cur_var_name)
                self.variable_dict[cur_var_name] = cur_var

    def CollectSettingConfig(self):
        for item in self.inputdata:
            if item == YAML_DEFINE_DICT:
                self.CollectDefine()
            elif item == YAML_SKU_DICT:
                self.CollectSku()
            elif item == YAML_DEFAULTSTORES_DICT:
                self.CollectDefaultStores()
            elif item == YAML_VARIABLE_DICT:
                self.CollectVariable()
            elif 'PcdsDynamicExHii' in item:
                _,arch,skuname,defaultstore = item.split('.')
                if skuname == 'DEFAULT' and defaultstore == 'STANDARD':
                    self.CollectStandardSettingConfig(item)
                else:
                    self.CollectCustomizedSettingConfig(item)

    def CollectStandardSettingConfig(self, standard_setting):
        self.standard_setting_config = self.inputdata[standard_setting]
        for item in self.standard_setting_config:
            variable_name = list(item.keys())[0]
            if variable_name in self.variable_list:
                current_var = self.variable_dict[variable_name]
                field_lists = item[variable_name]
                current_var.CollectField(field_lists)
                current_var.GenVarHeaderBuffer()

    def CollectCustomizedSettingConfig(self, customized_setting):
        _,arch,skuname,defaultstore = customized_setting.split('.')
        skuid = self.sku_dict[skuname]
        defaultstoreid = self.defaultstores_dict[defaultstore]
        self.customized_setting_config[(skuid, defaultstoreid)] = self.inputdata[customized_setting]
        for item in self.customized_setting_config[(skuid, defaultstoreid)]:
            variable_name = list(item.keys())[0]
            if variable_name in self.variable_list:
                current_var = self.variable_dict[variable_name]
                field_lists = item[variable_name]
                current_var.CollectCustomizedField(skuid, defaultstoreid, field_lists)

    def LoadYaml(self):
        self.CollectSettingConfig()
        self.GenDefaultBuffer()
        self.GenDeltaBuffer()

    def GenDefaultBuffer(self):
        NvStoreDataBuffer = b''
        for variable_name in self.variable_list:
            current_var = self.variable_dict[variable_name]
            NvStoreDataBuffer += current_var.GetVarDefaultBuffer()
        variable_storage_header_buffer = VariableMgr.PACK_VARIABLE_STORE_HEADER(len(NvStoreDataBuffer) + 28)
        self.nv_default_buffer = VariableMgr.AlignData(VariableMgr.PACK_DEFAULT_DATA(0, 0, VariableMgr.unpack_data(variable_storage_header_buffer+NvStoreDataBuffer)), 8)

    def GenDeltaBuffer(self):
        for variable_name in self.variable_list:
            current_var = self.variable_dict[variable_name]
            self.data_delta_structure_buffer += current_var.VarDeltaDataBuffer
    
    def DumpBinary(self):
        size = len(self.nv_default_buffer + self.data_delta_structure_buffer) + 16
        maxsize = self.VpdRegionSize if self.VpdRegionSize else size
        NV_Store_Default_Header = VariableMgr.PACK_NV_STORE_DEFAULT_HEADER(size, maxsize)
        default_var_binary = VariableMgr.format_data(NV_Store_Default_Header + self.nv_default_buffer + self.data_delta_structure_buffer)
        if default_var_binary:
            value_str = "{"
            default_var_bin_strip = [ data.strip("""'""") for data in default_var_binary]
            value_str += ",".join(default_var_bin_strip)
            value_str += "}"
            return value_str
        else:
            return ""


parser = argparse.ArgumentParser(description='''
View the Binary Structure of FD/FV/Ffs/Section, and Delete/Extract/Add/Replace a Ffs from/into a FV.
''')
parser.add_argument("-i", "--InputYamlFile", dest="InputYamlFile", nargs='+',
                    help="Given input variable Yaml file path")
parser.add_argument("-o", "--OutputBinaryFile", dest="OutputBinaryFile", nargs='+',
                    help="Given output variable bin file path")

def main():
    args=parser.parse_args()
    status=0
    try:
        inputfile = args.InputYamlFile[0]
        outputfile = args.OutputBinaryFile[0]
        with open(inputfile, 'r') as file:
            inputdata = yaml.load(file, Loader=yaml.FullLoader)
        yaml_config = YamlConfig(inputdata)
        yaml_config.LoadYaml()
        var_bin = yaml_config.DumpBinary()
        with open(outputfile, 'w') as file:
            file.write(var_bin)
    except Exception as e:
        print(e)
    return status


if __name__ == '__main__':
    exit(main())
