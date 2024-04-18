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
from subcommands.common import validate_arguments_for_radar_file, validate_arguments_for_environments_file
import data_files.common 
from data_files.radar_h5 import reoriente_sensor_data, get_radar_data_timestamp_from_index
from data_files.environments_excel import get_environment_information_between_timestamps
from miscellaneous import is_string_relative_numeric

RADAR_RANGE_MATPLOTLIB_IMSHOW = {
    'vmin': 0,
    'vmax': 500
}

def run_pca_subcommand(program_arguments):
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

    from sklearn.pipeline import Pipeline
    from sklearn.decomposition import PCA
    from sklearn.preprocessing import StandardScaler
    pca_model = PCA(n_components=2) 
    transformed_data = Pipeline([('scaler', StandardScaler()), ('pca', pca_model)]).fit_transform(reoriente_sensor_data(radar_file['data'][:20000].transpose()))
    plt.scatter(transformed_data[:,0], transformed_data[:,1])
    plt.show()
