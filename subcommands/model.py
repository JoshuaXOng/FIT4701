import sys
import os
import logging
import datetime
import itertools
import pickle
import argparse
import readline
import csv
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt, mpld3
import numpy as np 
import h5py
from sklearn.linear_model import LinearRegression
from subcommands.common import validate_arguments_for_radar_file
from data_files.radar_h5 import get_radar_file_start_timestamp, get_radar_file_end_timestamp, get_radar_data_around_timestamp 
from data_files.environments_excel import get_environment_information_start_timestamp, get_environment_information_end_timestamp 

def run_model_subcommand(program_arguments):
    validate_arguments_for_radar_file(program_arguments)

    logging.info('Path to environments file is... {}'.format(program_arguments.environment_file)) 
    if program_arguments.environment_file is None or not os.path.isfile(program_arguments.environment_file):
        raise Exception('Path to environments file does not point to a real file, was... {}'
        .format(program_arguments.environment_file))
    
    radar_file = h5py.File(program_arguments.radar_h5_file, 'r')
    start_timestamp = radar_file['timestamp'][()]
    sensors_dataset = radar_file['data']

    logging.info('Start timestamp in radar file is... {}'.format(start_timestamp))
    logging.info('Shape of data in radar file is... {}'.format(sensors_dataset.shape))

    environment_information = pd.read_excel(program_arguments.environment_file).iloc[1:, :]
    
    logging.info('Shape of the environment file... {}'.format(environment_information.shape))
    logging.info('Initial slice of environment file... {}'.format(environment_information.iloc[:2, :]))

    latest_start, earliest_end = find_greatest_overlap(radar_file, environment_information) 

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
        
        if row_index == 350:
            break
     
    moisture_model = LinearRegression()
    moisture_model.fit(
        np.array(list(map(lambda x: list(x[1][0]), radar_and_moisture))), 
        np.array(list(map(lambda x: x[0][1]['Leaf Moisture'], radar_and_moisture))), 
    )    
    #print(list(map(lambda x: list(x[1][0]), radar_and_moisture)))
    print(list(map(lambda x: x[0][1]['Leaf Moisture'], radar_and_moisture))[0])
    print(moisture_model.predict([radar_and_moisture[0][1][0]]))
    print(moisture_model.get_params())
    s = pickle.dumps(moisture_model)
    l = pickle.loads(s)
    print(l.predict([radar_and_moisture[0][1][0]]))

def find_greatest_overlap(radar_file, environment_information):
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
    return (latest_start, earliest_end)
