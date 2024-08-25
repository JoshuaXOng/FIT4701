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
from subcommands import validate_arguments_for_radar_file, validate_arguments_for_environments_file
import subcommands.plot
import data_files 
from data_files.radar_h5 import reoriente_sensor_data, get_radar_data_timestamp_from_index
from data_files.environments_excel import get_environment_information_between_timestamps
from miscellaneous import is_string_relative_numeric

def attach_pca_subcommand(plot_subcommands):
    pca_parser = plot_subcommands.add_parser('pca')
    pca_parser.set_defaults(func=run_pca_subcommand)

def validate_pca_subcommand(program_arguments):
    subcommands.plot.validate_plot_arguments(program_arguments) 

def run_pca_subcommand(program_arguments):
    validate_pca_subcommand(program_arguments)
    plot_pca_of_radar_data(
        program_arguments.radar_h5_file,
        program_arguments.environment_file,
        program_arguments.initial_region
    )

def plot_pca_of_radar_data(radar_h5_file, environment_file, initial_region):
    radar_file = h5py.File(radar_h5_file, 'r')
    start_timestamp = radar_file['timestamp'][()]
    sensors_dataset = radar_file['data']
    logging.info('Start timestamp in radar file is... {}'.format(start_timestamp))
    logging.info('Shape of data in radar file is... {}'.format(sensors_dataset.shape))

    environment_information = pd.read_excel(environment_file).iloc[1:, :]
    logging.info('Shape of the environment file... {}'.format(environment_information.shape))
    logging.info('Initial slice of environment file... {}'.format(environment_information.iloc[:2, :]))

    logging.info('Initial region is... {}'.format(initial_region)) 
    if initial_region is not None:
        if len(initial_region.split(',')) == 2:
            region_start, region_width = tuple(initial_region.split(','))
            if not region_start.isnumeric():
                raise Exception('Start of initial region program argument is inivalid, was... {}'
                .format(region_start))             
            if not region_width.isnumeric():
                raise Exception('Width of initial region program argument is invalid, was... {}'
                .format(region_width)) 
        else:
            raise Exception('Initial region program argument is invalid, was... {}'
            .format(initial_region))

        region_start = int(region_start)
        region_width = int(region_width)

    from sklearn.pipeline import Pipeline
    from sklearn.decomposition import PCA
    from sklearn.preprocessing import StandardScaler
    pca_model = PCA(n_components=2) 
    transformed_data = Pipeline([('scaler', StandardScaler()), ('pca', pca_model)]).fit_transform(reoriente_sensor_data(radar_file['data'][:20000].transpose()))
    plt.scatter(transformed_data[:,0], transformed_data[:,1])
    plt.show()
