import os
import xml.etree.ElementTree as ET

# Parse the XML file
tree = ET.parse('lib/params.xml')
root = tree.getroot()

# Helper function to parse sensor classification
def parse_classification(element):
    classification = {}
    for child in element:
        classification[child.tag] = int(child.text)
    return classification

# Function to parse the sensor configs
def parse_sensor_configs(root):
    sensor_configs = {}
    for sensor in root.find('sensor_configs'):
        name = sensor.attrib['name']
        sensor_configs[name] = {}
        
        # Parse epcs
        epcs = [epc.text for epc in sensor.find('epcs')]
        sensor_configs[name]['epc'] = epcs
        
        # Parse window and y_range
        sensor_configs[name]['window'] = float(sensor.find('window').text)
        sensor_configs[name]['y_range'] = int(sensor.find('y_range').text)
        
        # Parse classification if available
        classification_elem = sensor.find('classification')
        if classification_elem is not None:
            sensor_configs[name]['classification'] = parse_classification(classification_elem)
        else:
            sensor_configs[name]['classification'] = {}

    return sensor_configs

# Function to parse the repo_name
def parse_repo_name(root):
    return root.find('repo_name').text

# Function to parse the default sensor definition
def parse_sensor_def(root):
    return root.find('sensor_def').text

# Function to parse the read rate
def parse_read_rate(root):
    return int(root.find('read_rate').text)

# Function to parse the Impinj host IP
def parse_impinj_host_ip(root):
    return root.find('./impinj/host_ip').text

# Function to parse the Impinj host port
def parse_impinj_host_port(root):
    return int(root.find('./impinj/host_port').text)

# Function to parse store_data flag
def parse_store_data(root):
    return root.find('store_data').text.lower() == 'true'

# Function to parse the antenna reader configs
def parse_reader_configs(root):
    return {
        'reader': {
            'antenna': int(root.find('./antenna_reader_configs/reader/antenna').text),
            'rf_mode': int(root.find('./antenna_reader_configs/reader/rf_mode').text),
            'session': int(root.find('./antenna_reader_configs/reader/session').text),
            'tagPopulation': int(root.find('./antenna_reader_configs/reader/tagPopulation').text)
        },
        'report': {
            'channel': root.find('./antenna_reader_configs/report/channel').text.lower() == 'true',
            'rssi': root.find('./antenna_reader_configs/report/rssi').text.lower() == 'true',
            'timestamp': root.find('./antenna_reader_configs/report/timestamp').text.lower() == 'true',
            'count': root.find('./antenna_reader_configs/report/count').text.lower() == 'true',
            'phase': root.find('./antenna_reader_configs/report/phase').text.lower() == 'true'
        }
    }

# Load and parse the XML
SENSOR_CONFIGS = parse_sensor_configs(root)
repo_name = parse_repo_name(root)
SENSOR_DEF = parse_sensor_def(root)
read_rate = parse_read_rate(root)
IMPINJ_HOST_IP = parse_impinj_host_ip(root)
IMPINJ_HOST_PORT = parse_impinj_host_port(root)
STORE_DATA = parse_store_data(root)
CONFIGS = parse_reader_configs(root)

# Paths
directory = os.getcwd().split(repo_name)[0] + repo_name
DATA = os.path.join(directory, "data")
LIB = os.path.join(directory, 'lib')
SRC = os.path.join(directory, 'src')

# JAR files
octane_jar = os.path.join(LIB, "octane.jar")
interfaces_jar = os.path.join(LIB, "interfaces.jar")
jar_files = [octane_jar, interfaces_jar]
