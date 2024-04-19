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

def run_versus_subcommand(program_arguments):
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

    power_levels = None
    if program_arguments.power_levels is not None:
        power_levels = []
        for power_level in program_arguments.power_levels.split(','):
            if power_level.isdigit(): power_levels.append(int(power_level))
            else: logging.warning('Power level input appears to be incorrect')
    
    if power_levels == []:
        raise Exception('The input of power levels cannot be equivalent to an empty string')
    
    radar_and_moisture = data_files.common.get_overlap_as_aggregated(radar_file, environment_information)
    def to_radar_number_and_summed_moisture_entry(moisture_entry, radar_entry):
        if power_levels is None:
            radar_entry = radar_entry[0]
        else:
            _radar_entry = []
            for level_index, level_intensity in enumerate(radar_entry[0]):
                if level_index + 1 in power_levels:
                    _radar_entry.append(level_intensity)
            radar_entry = _radar_entry
        return (moisture_entry[1]['Leaf Moisture'], sum(radar_entry))
    summed_radar_and_moisture = list(map(
        lambda both_entries: to_radar_number_and_summed_moisture_entry(both_entries[0], both_entries[1]), 
        radar_and_moisture
    ))

    plt.title('Radar Level Versus Moisture')
    plt.xlabel('Moisture')
    plt.ylabel('Radar Level')
    plt.scatter(
        list(map(lambda x: x[0], summed_radar_and_moisture)), 
        list(map(lambda x: x[1], summed_radar_and_moisture))
    )

    plt.show() 
