import logging
import argparse
import readline
import csv
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt, mpld3
import numpy as np 
import h5py
import subcommands.plot.versus
import subcommands.plot.pca
import subcommands
from subcommands import validate_arguments_for_radar_file, validate_arguments_for_environments_file
import data_files
from data_files.radar_h5 import reoriente_sensor_data, get_radar_data_timestamp_from_index
from data_files.environments_excel import get_environment_information_between_timestamps
from miscellaneous import is_string_relative_numeric

def attach_plot_subcommand(root_subcommands):
    plot_parser = root_subcommands.add_parser('plot')
    plot_parser.add_argument('-r', '--radar-h5-file', 
        help='Path to the h5 radar file.')
    plot_parser.add_argument('-e', '--environment-file',
        help='Path to the csv that contains the moisture data.')
    plot_parser.add_argument('-i', '--initial-region', 
        help='Slice of initial viewing region of radar data, e.g., '
        'can exclude or set like \'3000,400\' (no relative start)')
    plot_parser.set_defaults(func=run_plot_subcommand)
    plot_subcommands = plot_parser.add_subparsers(title='subcommands')
    
    subcommands.plot.versus.attach_versus_subcommand(plot_subcommands)
    subcommands.plot.pca.attach_pca_subcommand(plot_subcommands)

def validate_plot_arguments(program_arguments):
    validate_arguments_for_radar_file(program_arguments)
    validate_arguments_for_environments_file(program_arguments)

RADAR_RANGE_MATPLOTLIB_IMSHOW = {
    'vmin': 0,
    'vmax': 500
}

def run_plot_subcommand(program_arguments):
    validate_plot_arguments(program_arguments)

    radar_file = h5py.File(program_arguments.radar_h5_file, 'r')
    start_timestamp = radar_file['timestamp'][()]
    sensors_dataset = radar_file['data']
    logging.info('Start timestamp in radar file is... {}'.format(start_timestamp))
    logging.info('Shape of data in radar file is... {}'.format(sensors_dataset.shape))

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

    run_plotting_loop(program_arguments, (region_start, region_width), radar_file, environment_information)

def run_plotting_loop(program_arguments, initial_region, radar_file, environment_information):
    region_start, region_width = initial_region
    
    subplots_figure, subplots_ax = plt.subplots(ncols=2, tight_layout=True)
    subplots_ax[0].set_title('Radar Heatmap')
    subplots_ax[0].set_ylabel('Distance Level')
    subplots_ax[0].set_xlabel('Time')
    subplots_ax[1].set_title('Moisture')
    subplots_ax[1].set_ylabel('Moisture Percentage')
    subplots_ax[1].set_xlabel('Time')

    if program_arguments.initial_region is None:
        sensors_data = reoriente_sensor_data(radar_file['data'][:])
        _environment_data = get_environment_information_between_timestamps(
            get_radar_data_timestamp_from_index(radar_file, 0),
            get_radar_data_timestamp_from_index(radar_file, -1)
        )
    else: 
        sensors_data = reoriente_sensor_data(
            radar_file['data'][region_start:region_start + region_width]
        )
        # TODO
        sensors_data = list(list(sensors_data)[50])
        # print(sensors_data)
        _environment_data = get_environment_information_between_timestamps(
            environment_information, 
            get_radar_data_timestamp_from_index(radar_file, region_start),
            get_radar_data_timestamp_from_index(radar_file, region_start + region_width)
        )
    # sensors_data = pca_model.transform(sensors_data.transpose()).transpose()
    # subplots_figure.colorbar(
        # subplots_ax[0].imshow(sensors_data, aspect='auto', **RADAR_RANGE_MATPLOTLIB_IMSHOW),
    # )
    subplots_ax[0].plot(sensors_data),
    _environment_data = list(map(lambda position_and_row: position_and_row[1]['Leaf Moisture'], _environment_data))
    print(_environment_data)
    subplots_ax[1].plot(_environment_data)
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
            _environment_data = get_environment_information_between_timestamps(
                environment_information, 
                get_radar_data_timestamp_from_index(radar_file, region_start),
                get_radar_data_timestamp_from_index(radar_file, region_start + region_width)
            )
        else:
            sensors_data = reoriente_sensor_data(radar_file['data'][:]) 
            _environment_data = get_environment_information_between_timestamps(
                get_radar_data_timestamp_from_index(radar_file, 0),
                get_radar_data_timestamp_from_index(radar_file, -1)
            )
        # sensors_data = pca_model.transform(sensors_data.transpose()).transpose()
        _environment_data = list(map(lambda position_and_row: position_and_row[1]['Leaf Moisture'], _environment_data))

        subplots_ax[0].imshow(sensors_data, aspect='auto', **RADAR_RANGE_MATPLOTLIB_IMSHOW)
        subplots_ax[1].plot(_environment_data)
        plt.draw()
        plt.pause(0.25)

