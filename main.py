import sys
import os
import logging
import time
import readline
import csv
import matplotlib
import matplotlib.pyplot as plt, mpld3
import numpy as np 
import h5py
import argparse

RADAR_RANGE_MATPLOTLIB_IMSHOW = {
    'vmin': 0,
    'vmax': 1000
}

def main():
    argument_parser = argparse.ArgumentParser()
    argument_parser.add_argument('-r', '--radar_h5_file', 
        help='Path to the h5 radar file.')
    argument_parser.add_argument('-i', '--initial_region', 
        help='Slice of initial viewing region of radar data, e.g., '
        'can exclude or set like \'3,400\' (no relative start)')
    argument_parser.add_argument('-e', '--environment_file',
        help='Path to the csv that contains the moisture data.')
    argument_parser.add_argument('-l', '--log_level')
    program_arguments = argument_parser.parse_args()
    
    if program_arguments.log_level is None:
        program_arguments.log_level = logging.INFO
    try:
        program_arguments.log_level = int(program_arguments.log_level)
    except Exception as e:
        raise Exception('Log level should be an integer, '
        'was... {}'.format(program_arguments.log_level))

    logging.basicConfig(level=program_arguments.log_level, format='%(asctime)s '
    '- %(name)s - %(levelname)s - %(message)s')

    logging.info('Path to radar file is... {}'.format(program_arguments.radar_h5_file))
    if not os.path.isfile(program_arguments.radar_h5_file):
        raise Exception('The path to the radar file does not exist, path was... {}'.format(
            program_arguments.radar_h5_file
        ))

    logging.info('Initial region is... {}'.format(program_arguments.initial_region)) 
    if program_arguments.initial_region is not None:
        if len(program_arguments.initial_region.split(',')) == 2:
            region_start, region_width = tuple(program_arguments.initial_region.split(','))
            if not region_start.isnumeric():
                raise Exception('Start of initial region program argument is inivalid, was... {}'
                .format(region_start))             
            if not region_width.isnumeric():
                raise Exception('Width of initial region program argument is invalid, was... {}'
                .format(region_width)) 
        else:
            raise Exception('Initial region program argument is invalid, was... {}'
            .format(program_arguments.initial_region))

        region_start = int(region_start)
        region_width = int(region_width)

    logging.info('Path to environments file is... {}'.format(program_arguments.environment_file)) 
    if program_arguments.environment_file is None and not os.path.isfile(program_arguments.environment_file):
        raise Exception('Path to environments file does not point to a real file, was... {}'
        .format(program_arguments.environment_file))
    
    radar_file = h5py.File(program_arguments.radar_h5_file, 'r')
    start_timestamp = radar_file['timestamp'][()]
    sensors_dataset = radar_file['data']
    def reoriente_sensor_data(sensors_data):
        return sensors_data.swapaxes(0, 1)[:][0].swapaxes(0, 1)

    logging.info('Start timestamp in radar file is... {}'.format(start_timestamp))
    logging.info('Shape of data in radar file is... {}'.format(sensors_dataset.shape))

    if program_arguments.environment_file is not None:
        environment_information = []
        with open(program_arguments.environment_file, newline='') as file_contents:
            for row_index, environment_row in enumerate(csv.reader(file_contents)):
                if row_index == 0 or row_index == 1: 
                    continue            
                environment_timestamp, environment_moisture \
                = time.strptime(environment_row[0], "%m/%d/%y %H:%M"), environment_row[6]
                environment_information.append((environment_timestamp, environment_moisture))

    subplots_figure, subplots_ax = plt.subplots()
    subplots_ax.set_title('Radar Heatmap')
    subplots_ax.set_ylabel('Distance Level')
    subplots_ax.set_xlabel('Time')
    if program_arguments.initial_region is None:
        sensors_data = reoriente_sensor_data(radar_file['data'][:])
    else: 
        sensors_data = reoriente_sensor_data(
            radar_file['data'][region_start:region_start + region_width])
    subplots_figure.colorbar(
        subplots_ax.imshow(sensors_data, **RADAR_RANGE_MATPLOTLIB_IMSHOW),
    )
    plt.show(block=False)
    plt.draw()
    plt.pause(0.25)
    while True:
        usage_hint = 'Invalid input ({})'
        user_input = input('Load different region of data, can be relative (e.g., \'+2,1000\') '
        'or absolute (e.g., \'2,1000\'): ')

        logging.info('User input is... {}'.format(user_input))
        
        if user_input != '':
            if len(user_input.split(',')) == 2:
                candidate_region_start, candidate_region_width = tuple(user_input.split(','))
                if not candidate_region_start.isnumeric() and \
                not is_string_relative_numeric(candidate_region_start):
                    print(usage_hint.format('start'))
                    continue
                if not candidate_region_width.isnumeric():
                    print(usage_hint.format('width'))
                    continue
            else:
                print(usage_hint.format('start and width'))            
                continue

            if is_string_relative_numeric(candidate_region_start):        
                region_start = region_start + int(candidate_region_start) 
            else:
                region_start = int(candidate_region_start)
            region_width = int(candidate_region_width)

            sensors_data = reoriente_sensor_data(radar_file['data'][region_start:region_start + region_width]) 
        else:
            sensors_data = reoriente_sensor_data(radar_file['data'][:]) 

        subplots_ax.imshow(sensors_data, **RADAR_RANGE_MATPLOTLIB_IMSHOW)
        plt.draw()
        plt.pause(0.25)

def is_string_relative_numeric(string):
    if len(string) >= 2 and string[0] in ['-', '+'] and string[1:].isnumeric():
        return True 
    else:
        return False

if __name__ == '__main__':
    main()
