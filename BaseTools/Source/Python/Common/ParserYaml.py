import yaml
import os
from struct import pack, unpack
from VariableAttributes import VariableAttributes
from AutoGen.GenVar import VariableMgr
from Common import StringUtils

STANDARD_SETTING = 'PcdsDynamicExHii.common.DEFAULT.STANDARD'
MANUFACTURING_SETTING = 'PcdsDynamicExHii.common.DEFAULT.MANUFACTURING'
YAML_DEFINE_DICT = 'defines'
YAML_SKU_DICT = 'sku'
YAML_DEFAULTSTORES_DICT = 'defaultstores'
YAML_VARIABLE_DICT = 'variable'


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

        self.VarNameBuffer = b''
        self.VarFieldList = []
        self.VarFieldDict = {}
        self.MacroDict = {}
        self.VarDefaultSetting = []
        self.VarManufacturingSetting = []

    def GetVarName(self):
        self.VarNameBuffer = VariableMgr.PACK_VARIABLE_NAME(StringUtils.StringToArray(self.VarName))

    def GetVarAttrProp(self):
        self.VarAttr, self.VarProp = VariableAttributes.GetVarAttributes(self.VarAttribute)

    def GetVarGuid(self):
        if '-' in self.VarGuid:
            self.VarGuid = self.VarGuid.split('-')

    def CollectManufacturingField(self, field_lists):
        for field in field_lists:
            field_name = list(field.keys())[0]
            if field_name not in self.VarManufacturingSetting:
                new_field = {}
                new_field[field_name] = {}
                field_length = field[field_name]['length']
                field_length = self.GetFieldLengthFromMacro(field_length, field_name)
                field_value = field[field_name]['value']
                new_field[field_name]['field_length'] = field_length
                new_field[field_name]['field_default_value'] = field_value
                new_field[field_name]['field_offset'] = self.VarFieldDict[field_name][field_name]['field_offset']
                self.VarManufacturingSetting.append(new_field)

    def CollectField(self, field_lists):
        cur_offset = 0
        for field in field_lists:
            field_length = self.AddNewField(field, cur_offset)
            cur_offset += int(field_length)

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
        return field_length

    def GetFieldLengthFromMacro(self, field_length, field_name):
        if type(field_length) == str:
            if field_length.startswith('$'):
                field_length = field_length.replace('$(', '').replace(')', '')
            if field_length in self.MacroDict:
                field_length = self.MacroDict[field_length]
            else:
                raise 'Unknown Field Length: {}'.format(field_name)
        return field_length

    def GetVarManufacturingSetting(self):
        self.VarDefaultSetting = self.VarFieldList

    def GetVarDefaultSetting(self):
        self.VarDefaultSetting = self.VarFieldList

class YamlConfig():
    def __init__(self, inputdata='') -> None:
        self.inputdata = inputdata
        self.define_dict = {}
        self.sku_dict = {}
        self.defaultstores_dict = {}
        self.variable_dict = {}
        self.standard_setting_config = {}
        self.manufacturing_setting_config = {}
        self.variable_list = []

    def ReadVariable(self, target_variable):
        target_variable_name = list(target_variable.keys())[0]
        var_content = target_variable[target_variable_name]
        yaml_var = YamlVariable(target_variable_name)
        yaml_var.MacroDict = self.define_dict
        for item in var_content:
            if 'Name' in item:
                yaml_var.VarName = item['Name']
                yaml_var.GetVarName()
            if 'PcdName' in item:
                yaml_var.VarPcdName = item['PcdName']
            if 'Guid' in item:
                yaml_var.VarGuid = item['Guid']
            if 'DefaultValue' in item:
                yaml_var.VarDefaultValue = item['DefaultValue']
            if 'VarAttribute' in item:
                yaml_var.VarAttribute = item['VarAttribute']
                yaml_var.GetVarAttrProp()
            if 'HeaderFile' in item:
                yaml_var.VarHeaderFile = item['HeaderFile']
        return target_variable_name, yaml_var

    def CollectDefine(self):
        if YAML_DEFINE_DICT in self.inputdata:
            self.define_dict = self.inputdata[YAML_DEFINE_DICT]

    def CollectSku(self):
        if YAML_SKU_DICT in self.inputdata:
            self.sku_dict = self.inputdata[YAML_SKU_DICT]

    def CollectDefaultStores(self):
        if YAML_DEFAULTSTORES_DICT in self.inputdata:
            self.defaultstores_dict = self.inputdata[YAML_DEFAULTSTORES_DICT]

    def CollectVariable(self):
        if YAML_VARIABLE_DICT in self.inputdata:
            variable_dict = self.inputdata[YAML_VARIABLE_DICT]
        for item in variable_dict:
            cur_var_name, cur_var = self.ReadVariable(item)
            if cur_var_name not in self.variable_list:
                self.variable_list.append(cur_var_name)
                self.variable_dict[cur_var_name] = cur_var

    def CollectStandardSettingConfig(self):
        if STANDARD_SETTING in self.inputdata:
            self.standard_setting_config = self.inputdata[STANDARD_SETTING]
            for item in self.standard_setting_config:
                variable_name = list(item.keys())[0]
                if variable_name in self.variable_list:
                    current_var = self.variable_dict[variable_name]
                    field_lists = item[variable_name]
                    current_var.CollectField(field_lists)

    def CollectManufacturingSettingConfig(self):
        if MANUFACTURING_SETTING in self.inputdata:
            self.manufacturing_setting_config = self.inputdata[MANUFACTURING_SETTING]
            for item in self.manufacturing_setting_config:
                variable_name = list(item.keys())[0]
                if variable_name in self.variable_list:
                    current_var = self.variable_dict[variable_name]
                    field_lists = item[variable_name]
                    current_var.CollectManufacturingField(field_lists)

    def LoadYaml(self):
        self.CollectDefine()
        self.CollectSku()
        self.CollectDefaultStores()
        self.CollectVariable()
        self.CollectStandardSettingConfig()
        self.CollectManufacturingSettingConfig()
        print()


if __name__ == '__main__':
    inputfile = r'C:\Users\yuweiche\Code\Dev\edk2\YamlEnable\temp.yaml'
    with open(inputfile, 'r') as file:
        inputdata = yaml.load(file, Loader=yaml.FullLoader)
    yaml_config = YamlConfig(inputdata)
    yaml_config.LoadYaml()
