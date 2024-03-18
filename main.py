import sys
import os
import logging
import datetime
import itertools
import bisect 
import argparse
import readline
import csv
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt, mpld3
import numpy as np 
import h5py
from sklearn.linear_model import LinearRegression

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
    def get_radar_file_start_timestamp(radar_file):
        return datetime.datetime.fromtimestamp(
            min(radar_file['sample_times'][:])
        ) 
    def get_radar_file_end_timestamp(radar_file):
        return datetime.datetime.fromtimestamp(
            max(radar_file['sample_times'][:])
        ) 
    def get_radar_data_around_timestamp(radar_file, center_datetime, leniency_timedelta):
        if radar_file['sample_times'].shape[0] != radar_file['data'].shape[0]:
            logging.warning('Data and timestamps are not of the same length.')
        
        radar_timestamps = list(map(lambda x: datetime.datetime.fromtimestamp(x), radar_file['sample_times'][:]))
        candidate_indices = [bisect.bisect_left(radar_timestamps, center_datetime),
            bisect.bisect_right(radar_timestamps, center_datetime)]
        get_delta = lambda x: abs((center_datetime - x).total_seconds())
        candidate_index = min(candidate_indices, key=lambda x: get_delta(radar_timestamps[x]))
        if get_delta(radar_timestamps[candidate_index]) \
        >= leniency_timedelta.total_seconds():
            return None

        return radar_file['sample_times'][candidate_index]

    logging.info('Start timestamp in radar file is... {}'.format(start_timestamp))
    logging.info('Shape of data in radar file is... {}'.format(sensors_dataset.shape))

    if program_arguments.environment_file is not None:
        environment_information = pd.read_excel(program_arguments.environment_file).iloc[1:, :]
        def environment_timestamp_to_datetime(environment_timestamp):
            return datetime.datetime.strptime(environment_timestamp, "%m/%d/%y %H:%M")
        def get_environment_information_start_timestamp(environment_information):
            return min(environment_information.iloc[:, 0])
        def get_environment_information_end_timestamp(environment_information):
            return max(environment_information.iloc[:, 0])
        def get_environment_information_around_timestamp(environment_information, center_datetime, leniency_timedelta):
            closest_row, smallest_timedelta = None, None
            for row_information in environment_information.iterrows():      
                row_timestamp = row_information[1]['TIMESTAMP'] 
                candidate_timedelta = center_datetime - row_timestamp
                if abs(candidate_timedelta.total_seconds()) < leniency_timedelta.total_seconds():
                    if (closest_row is None and smallest_timedelta is None) \
                    or (abs(candidate_timedelta.total_seconds()) < smallest_timedelta.total_seconds()):
                        closest_row, smallest_timedelta = row_information, candidate_timedelta
            return closest_row
        
        logging.info('Shape of the environment file... {}'.format(environment_information.shape))
        logging.info('Initial slice of environment file... {}'.format(environment_information.iloc[:2, :]))

        radar_start, radar_end = get_radar_file_start_timestamp(radar_file), get_radar_file_end_timestamp(radar_file)
        environment_start, environment_end = get_environment_information_start_timestamp(environment_information), \
        get_environment_information_end_timestamp(environment_information)
        
        logging.info('Radar data starts at... {}, and ends at... {}'.format(radar_start, radar_end)) 
        logging.info('Environment information starts at... {}, and ends at... {}'.format(environment_start, environment_end))
        if radar_start is None  or radar_end is None or environment_start is None or environment_end is None:
            raise Exception('Radar data interval ({} to {}) or environment data ({} to {}) interval based on'
            ' supplied data is in-complete.'.format(radar_start, radar_end, environment_start, environment_end))
        
        latest_start = max(radar_start, environment_start)
        earliest_end = min(radar_end, environment_end)
        
        radar_and_moisture = []
        for row_index, _environment_information in enumerate(environment_information.iterrows()):   
            logging.debug('At index {} of {}'.format(row_index, environment_information.shape[0]))

            environment_timestamp = _environment_information[1]['TIMESTAMP'] 
            
            if environment_timestamp < latest_start or environment_timestamp > earliest_end:
                logging.debug('Skipping finding corresponding radar data, latest start is... {}, earliest end is... {} and '
                'environment timestamp is... {}'.format(latest_start, earliest_end, environment_timestamp))
                continue
            
            corresponding_radar = get_radar_data_around_timestamp(radar_file, environment_timestamp, datetime.timedelta(seconds=1))
            
            if corresponding_radar is None:
                logging.warning('No corresponding radar data found for environment data of timestamp... {}'.format(environment_timestamp)) 
                continue 
            
            radar_and_moisture.append((_environment_information, corresponding_radar))
            
            if row_index == 366:
                break

        moisture_model = LinearRegression()
        x = []
        y = []
        for i in range(0, 1000):
            x.append([i])
            y.append(i) 
        print(x[:4], y[:4])
        moisture_model.fit(x, y)    
        print(moisture_model.predict([[6]]))
        return 

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

def get_sorted_iterator_of_radar_data(radar_file):
    pass

if __name__ == '__main__':
    main()
