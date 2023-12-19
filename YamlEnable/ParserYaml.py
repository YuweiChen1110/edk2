import yaml

STANDARD_SETTING = '[PcdsDynamicExHii.common.DEFAULT.STANDARD]'
MANUFACTURING_SETTING = '[PcdsDynamicExHii.common.DEFAULT.MANUFACTURING]'

def LoadYaml(inputfile):
    with open(inputfile, 'r') as file:
        inputdata = yaml.load(file, Loader=yaml.FullLoader)
    print(inputdata)

if __name__ == '__main__':
    inputfile = r'temp.yaml'
    LoadYaml(inputfile)
