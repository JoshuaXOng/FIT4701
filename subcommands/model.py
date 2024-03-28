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
from subcommands.common import validate_arguments_for_radar_file, validate_arguments_for_environments_file
import data_files.common
from data_files.radar_h5 import get_radar_data_around_timestamp 

def run_model_subcommand(program_arguments):
    preprocessed_data_file = 'radar_and_moisture_preprocessed.pkl'

    logging.info('Path to file containing radar data feed model... {}'.format(program_arguments.guess_for))
    logging.info('Path to model file is... {}'.format(program_arguments.model))
    if program_arguments.guess_for is not None and program_arguments.model is not None:
        if not os.path.isfile(program_arguments.model):
            raise Exception('The model file is invalid... {}'.format(program_arguments.model))

        with open(program_arguments.model, 'rb') as save_file:
            moisture_model = pickle.load(save_file)
        
        with open(program_arguments.guess_for, 'r') as guess_for:
            _guess_for = [json.loads(guess_for.read())]
        print("Moisture prediction:", moisture_model.predict(_guess_for))

        with open(preprocessed_data_file, 'rb') as save_file:
            radar_and_moisture = pickle.load(save_file)
        logging.info("Accuracy: {}".format(moisture_model.score(
            np.array(list(map(lambda x: list(x[1][0]), radar_and_moisture))), 
            np.array(list(map(lambda x: x[0][1]['Leaf Moisture'], radar_and_moisture))), 
        )))

        return

    validate_arguments_for_radar_file(program_arguments)
    
    radar_file = h5py.File(program_arguments.radar_h5_file, 'r')
    start_timestamp = radar_file['timestamp'][()]
    sensors_dataset = radar_file['data']

    logging.info('Start timestamp in radar file is... {}'.format(start_timestamp))
    logging.info('Shape of data in radar file is... {}'.format(sensors_dataset.shape))

    validate_arguments_for_environments_file(program_arguments)

    environment_information = pd.read_excel(program_arguments.environment_file).iloc[1:, :]
    
    logging.info('Shape of the environment file... {}'.format(environment_information.shape))
    logging.info('Initial slice of environment file... {}'.format(environment_information.iloc[:2, :]))

    latest_start, earliest_end = data_files.common.find_greatest_overlap(radar_file, environment_information) 
    if not os.path.isfile(preprocessed_data_file):
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
        with open(preprocessed_data_file, 'wb') as save_file:
            pickle.dump(radar_and_moisture, save_file)
            logging.info('Pickled processed radar and moisture to {}.'.format(preprocessed_data_file))
    else:
        with open(preprocessed_data_file, 'rb') as save_file:
            radar_and_moisture = pickle.load(save_file)
     
    moisture_model = LinearRegression()
    moisture_model.fit(
        np.array(list(map(lambda x: list(x[1][0]), radar_and_moisture))), 
        np.array(list(map(lambda x: x[0][1]['Leaf Moisture'], radar_and_moisture))), 
    )    

    file_name = 'moisture_model_{}_{}.pkl'.format(datetime.datetime.now(), uuid.uuid4())
    with open(file_name, 'wb') as save_file:
        pickle.dump(moisture_model, save_file) 
        print('Pickled model to {}'.format(file_name))
