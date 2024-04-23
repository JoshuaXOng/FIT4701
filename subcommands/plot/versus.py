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
import subcommands.plot
from subcommands import validate_arguments_for_radar_file, validate_arguments_for_environments_file
import data_files
from data_files.radar_h5 import reoriente_sensor_data, get_radar_data_timestamp_from_index
from data_files.environments_excel import get_environment_information_between_timestamps
from miscellaneous import is_string_relative_numeric

def attach_versus_subcommand(plot_subcommands):
    versus_parser = plot_subcommands.add_parser('versus')
    versus_parser.add_argument('-p', '--power-levels', 
        help='Whether or not, and to determine which levels of power'
        'to plot.')
    versus_parser.add_argument('-x', '--export-dir', 
        help='If specified, will save the plot image to the supplied directory')
    versus_parser.set_defaults(func=run_versus_subcommand)
    
def validate_versus_subcommand(program_arguments):
    subcommands.plot.validate_plot_arguments(program_arguments) 
    # TODO: Check between 1 and 414 
    if program_arguments.export_dir is not None and not os.path.isdir(program_arguments.export_dir):
        raise Exception("Value of export directory does not point to an actual directory.")

def run_versus_subcommand(program_arguments):
    validate_versus_subcommand(program_arguments)

    radar_file = h5py.File(program_arguments.radar_h5_file, 'r')
    start_timestamp = radar_file['timestamp'][()]
    sensors_dataset = radar_file['data']
    logging.info('Start timestamp in radar file is... {}'.format(start_timestamp))
    logging.info('Shape of data in radar file is... {}'.format(sensors_dataset.shape))

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
    
    radar_and_moisture = data_files.get_overlap_as_aggregated(radar_file, environment_information)
    grouped_by_moisture = itertools.groupby(
        radar_and_moisture,
        lambda radar_and_moisture: radar_and_moisture[0][1]['Leaf Moisture']
    )
    def to_radar_number_and_summed_moisture_entry_for_group(grouped_entry):
        running_sum = 0
        for index, (moisture_entry, radar_entry) in enumerate(grouped_entry[1]):
            running_sum += to_radar_number_and_summed_moisture_entry(moisture_entry, radar_entry)[1]
        return (grouped_entry[0], running_sum / (index + 1)) 
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
        lambda grouped_entry: to_radar_number_and_summed_moisture_entry_for_group(grouped_entry), 
        grouped_by_moisture 
    ))
    
    summed_radar_and_moisture = sorted(summed_radar_and_moisture, key=lambda summed_radar_and_moisture: summed_radar_and_moisture[0])

    plt.title('Radar Level Versus Moisture')
    plt.xlabel('Moisture')
    plt.ylabel('Radar Level')
    plt.plot(
        list(map(lambda x: x[0], summed_radar_and_moisture)), 
        list(map(lambda x: x[1], summed_radar_and_moisture))
    )

    if program_arguments.export_dir is not None:
        plt.savefig(os.path.join(program_arguments.export_dir, "radar_versus_moisture_p={}".format(
            program_arguments.power_levels
        )))
    else:
        plt.show()
