from configparser import ConfigParser

file = 'config.ini'
config = ConfigParser()
config.read(file)

print(config['path'])