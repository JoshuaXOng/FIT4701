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
from subcommands.common import validate_arguments_for_radar_file
from data_files.radar_h5 import reoriente_sensor_data
from miscellaneous import is_string_relative_numeric

RADAR_RANGE_MATPLOTLIB_IMSHOW = {
    'vmin': 0,
    'vmax': 1000
}

def run_plot_subcommand(program_arguments):
    validate_arguments_for_radar_file(program_arguments)

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

    radar_file = h5py.File(program_arguments.radar_h5_file, 'r')
    start_timestamp = radar_file['timestamp'][()]
    sensors_dataset = radar_file['data']

    logging.info('Start timestamp in radar file is... {}'.format(start_timestamp))
    logging.info('Shape of data in radar file is... {}'.format(sensors_dataset.shape))

    run_plotting_loop(program_arguments, (region_start, region_width), radar_file)

def run_plotting_loop(program_arguments, initial_region, radar_file):
    region_start, region_width = initial_region

    subplots_figure, subplots_ax = plt.subplots(tight_layout=True)
    subplots_ax.set_title('Radar Heatmap')
    subplots_ax.set_ylabel('Distance Level')
    subplots_ax.set_xlabel('Time')
    if program_arguments.initial_region is None:
        sensors_data = reoriente_sensor_data(radar_file['data'][:])
    else: 
        sensors_data = reoriente_sensor_data(
            radar_file['data'][region_start:region_start + region_width])
    subplots_figure.colorbar(
        subplots_ax.imshow(sensors_data, aspect='auto', **RADAR_RANGE_MATPLOTLIB_IMSHOW),
    )
    plt.show(block=False)
    plt.draw()
    plt.pause(0.25)
    while True:
        usage_hint = 'Invalid input ({})'
        user_input = input('Load different region of data, can be relative (e.g., \'+2000,1000\') '
        'or absolute (e.g., \'2000,1000\'): ')

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

        subplots_ax.imshow(sensors_data, aspect='auto', **RADAR_RANGE_MATPLOTLIB_IMSHOW)
        plt.draw()
        plt.pause(0.25)
