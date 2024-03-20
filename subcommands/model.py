import sys
import os
import logging
import datetime
import itertools
import pickle
import uuid
import argparse
import ast
import json
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
    logging.info('Path to file containing radar data feed model... {}'.format(program_arguments.guess_for))
    logging.info('Path to model file is... {}'.format(program_arguments.model))
    if program_arguments.guess_for is not None and program_arguments.model is not None:
        if not os.path.isfile(program_arguments.model):
            raise Exception('The model file is invalid... {}'.format(program_arguments.model))

        with open(program_arguments.model, 'rb') as save_file:
            moisture_model = pickle.load(save_file)
        
        with open(program_arguments.guess_for, 'r') as guess_for:
            _guess_for = [json.loads(guess_for.read())]
        print(moisture_model.predict(_guess_for))

        return

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
    #print(radar_and_moisture[0][1][0])
     
    moisture_model = LinearRegression()
    moisture_model.fit(
        np.array(list(map(lambda x: list(x[1][0]), radar_and_moisture))), 
        np.array(list(map(lambda x: x[0][1]['Leaf Moisture'], radar_and_moisture))), 
    )    

    file_name = 'moisture_model_{}_{}.pkl'.format(datetime.datetime.now(), uuid.uuid4())
    with open(file_name, 'wb') as save_file:
        pickle.dump(moisture_model, save_file) 
        print('Pickled model to {}'.format(file_name))

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
