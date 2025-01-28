import configparser

config = configparser.ConfigParser()

config.add_section('path')

config.set('path','base_path',r'\files')

with open('config.ini','w') as file:
    config.write(file)