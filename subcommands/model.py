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
from subcommands import validate_arguments_for_radar_file, validate_arguments_for_environments_file
import data_files
from data_files.radar_h5 import get_radar_data_around_timestamp 

def attach_model_subcommand(root_subcommands):
    model_parser = root_subcommands.add_parser('model')
    model_parser.add_argument('-r', '--radar_h5_file', 
      help='Path to the h5 radar file.')
    model_parser.add_argument('-e', '--environment_file',
      help='Path to the csv that contains the moisture data.')
    model_parser.add_argument('-g', '--guess_for',
      help='Path to a file containing radar data to be fed to the model.')
    model_parser.add_argument('-m', '--model',
      help='Path to a file containing the model.')
    model_parser.set_defaults(func=run_model_subcommand)

def validate_model_arguments(program_arguments):
    validate_arguments_for_radar_file(program_arguments)
    validate_arguments_for_environments_file(program_arguments)
    moisture_model = program_arguments.model
    if moisture_model is not None and not os.path.isfile(moisture_model):
        raise Exception('The model file is invalid... {}'.format(moisture_model))
    guessing_input = program_arguments.guess_for
    if guessing_input is not None and not os.path.isfile(guessing_input):
        raise Exception('The guessing input file is invalid... {}'.format(guessing_input))

def run_model_subcommand(program_arguments):
    validate_model_arguments(program_arguments)

    logging.info('Path to file containing radar data feed model... {}'.format(program_arguments.guess_for))
    logging.info('Path to model file is... {}'.format(program_arguments.model))
    if program_arguments.guess_for is not None and program_arguments.model is not None:
        perform_guess(program_arguments)
    else:
        perform_training(program_arguments)

def perform_guess(program_arguments):
    with open(program_arguments.model, 'rb') as save_file:
        moisture_model = pickle.load(save_file)
    
    with open(program_arguments.guess_for, 'r') as guess_for:
        _guess_for = [json.loads(guess_for.read())]
    print("Moisture prediction:", moisture_model.predict(_guess_for))

    with open(data_files.PREPROCESSED_DATA_FILE, 'rb') as save_file:
        radar_and_moisture = pickle.load(save_file)
    logging.info("Accuracy: {}".format(moisture_model.score(
        np.array(list(map(lambda x: list(x[1][0]), radar_and_moisture))), 
        np.array(list(map(lambda x: x[0][1]['Leaf Moisture'], radar_and_moisture))), 
    )))

def perform_training(program_arguments):
    radar_file = h5py.File(program_arguments.radar_h5_file, 'r')
    start_timestamp = radar_file['timestamp'][()]
    sensors_dataset = radar_file['data']
    logging.info('Start timestamp in radar file is... {}'.format(start_timestamp))
    logging.info('Shape of data in radar file is... {}'.format(sensors_dataset.shape))

    environment_information = pd.read_excel(program_arguments.environment_file).iloc[1:, :]
    logging.info('Shape of the environment file... {}'.format(environment_information.shape))
    logging.info('Initial slice of environment file... {}'.format(environment_information.iloc[:2, :]))

    radar_and_moisture = data_files.get_overlap_as_aggregated(radar_file, environment_information)
     
    moisture_model = LinearRegression()
    moisture_model.fit(
        np.array(list(map(lambda x: list(x[1][0]), radar_and_moisture))), 
        np.array(list(map(lambda x: x[0][1]['Leaf Moisture'], radar_and_moisture))), 
    )    

    file_name = 'moisture_model_{}_{}.pkl'.format(datetime.datetime.now(), uuid.uuid4())
    with open(file_name, 'wb') as save_file:
        pickle.dump(moisture_model, save_file) 
        print('Pickled model to {}'.format(file_name))
