STANDARD_SETTING = '[PcdsDynamicExHii.common.DEFAULT.STANDARD]'
MANUFACTURING_SETTING = '[PcdsDynamicExHii.common.DEFAULT.MANUFACTURING]'

def CollectDSCInfo():
    inputfile = r'E:\Code\oks\Intel\Build_ori\OakStreamRpPkg\SetupDefaultValue.dsc.no_macros'
    var_dict = {}
    with open(inputfile, 'r') as file:
        filedata = file.readlines()
    for line in filedata:
        if line.startswith('#') or line.replace('\n', '').strip() == '':
            continue
        if STANDARD_SETTING in line:
            var_dict[STANDARD_SETTING] = {}
        if MANUFACTURING_SETTING in line:
            var_dict[MANUFACTURING_SETTING] = {}
        if line.startswith('gStructPcdTokenSpaceGuid'):
            if line.split('|')[1].startswith('L'):
                continue
            else:
                varlist = line.split('|')
                varname = varlist[0].split('.')[2]
                varvalue = varlist[1]
                if MANUFACTURING_SETTING in var_dict:
                    var_dict[MANUFACTURING_SETTING][varname] = varvalue
                else:
                    var_dict[STANDARD_SETTING][varname] = varvalue
    return var_dict

def ConsumeHeaderFile():
    var_dict = CollectDSCInfo()
    inputfile = r'Info.txt'
    outputdata = ''

    with open(inputfile, 'r') as file:
        filedata = file.readlines()

    for line in filedata:
        if line.startswith('//') or line.replace('\n', '').strip() == '':
            continue
        elif line.startswith('#ifdef') or line.startswith('#endif'):
            outputdata += line
            continue

        VarInfo = line.split(';')[0]
        VarList = VarInfo.split(' ')
        VarType = VarList[0]
        VarName = VarList[-1]
        VarLen = 1
        if '[' in VarName:
            VarLen = VarName.split('[')[1].split(']')[0]
            VarName = VarName.split('[')[0]
        outputdata += '{}- {} :\n'.format(' '*4, VarName)
        if VarType == 'UINT8':
            if type(VarLen) == type('str'):
                outputdata += '{}length   : {}\n'.format(' '*6, VarLen)
            else:
                VarLen = VarLen * 0x01
                outputdata += '{}length   : {}\n'.format(' '*6, hex(VarLen))
        elif VarType == 'UINT16':
            if type(VarLen) == type('str'):
                outputdata += '{}length   : {}\n'.format(' '*6, VarLen+' * 0x02')
            else:
                VarLen = VarLen * 0x02
                outputdata += '{}length   : {}\n'.format(' '*6, hex(VarLen))
        elif VarType == 'UINT32':
            if type(VarLen) == type('str'):
                outputdata += '{}length   : {}\n'.format(' '*6, VarLen+' * 0x04')
            else:
                VarLen = VarLen * 0x04
                outputdata += '{}length   : {}\n'.format(' '*6, hex(VarLen))
        elif VarType == 'UINT64':
            if type(VarLen) == type('str'):
                outputdata += '{}length   : {}\n'.format(' '*6, VarLen+' * 0x08')
            else:
                VarLen = VarLen * 0x08
                outputdata += '{}length   : {}\n'.format(' '*6, hex(VarLen))
        if VarName in var_dict[STANDARD_SETTING]:
            VarValue = var_dict[STANDARD_SETTING][VarName]
            outputdata += '{}value    : {}'.format(' '*6, VarValue)
        else:
            outputdata += '{}value    : 0x00\n'.format(' '*6)

    with open('Info.yaml', 'w') as outputfile:
        outputfile.write(outputdata)


if __name__ == '__main__':
    ConsumeHeaderFile()
