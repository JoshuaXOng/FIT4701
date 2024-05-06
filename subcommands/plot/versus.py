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

    radar_and_moisture_grouped_by_moisture = sorted(
        map(
            lambda x: (x[0], list(x[1])),
            itertools.groupby(
                radar_and_moisture,
                lambda radar_and_moisture: radar_and_moisture[0][1]['Leaf Moisture']
            )
        ),
        key=lambda x: x[0]
    )
    def produce_radar_versus_moisture_lines(radar_and_moisture_grouped_by_moisture, power_levels, aggregate_or_individual):
        from copy import deepcopy
        radar_and_moisture = []
        get_average = lambda x: np.add.reduce(x, axis=0) / len(x) 
        for group_index, (moisture_percentage, radar_and_moisture_entry) in enumerate(radar_and_moisture_grouped_by_moisture):
            radar_and_moisture.append((moisture_percentage, get_average(list(radar_and_moisture_entry)[0][1])))

        radar_versus_moisture_lines = [] 

        if aggregate_or_individual == "aggregate":
            def aggregate_radar_levels(radar_intensities):
                aggregated_radar = 0
                for power_level in (power_levels if power_levels is not None else range(1, 415)):
                    aggregated_radar += radar_intensities[power_level - 1] 
                return aggregated_radar 
            radar_versus_moisture_lines.append((
                list(map(lambda x: x[0], radar_and_moisture)),
                list(map(lambda x: aggregate_radar_levels(x[1]), radar_and_moisture)),
            ))
        elif aggregate_or_individual == "individual":
            for power_level in (power_levels if power_levels is not None else range(1, 415)):
                moisture_percentages = list(map(lambda x: x[0], radar_and_moisture))
                radar_intensities = list(map(lambda x: x[1][power_level - 1], radar_and_moisture))
                radar_versus_moisture_lines.append((moisture_percentages, radar_intensities)) 
        else:
            raise Exception("Invalid choice for aggregate or invididual.") 
        
        return radar_versus_moisture_lines
    radar_versus_moisture_lines = produce_radar_versus_moisture_lines(radar_and_moisture_grouped_by_moisture, power_levels, "individual")

    def plot_radar_versus_moisture_lines(radar_versus_moisture_lines):
        from math import floor, ceil
        subplot_width = 5
        subplot_height = ceil(len(radar_versus_moisture_lines) / subplot_width)
        subplots_figure, subplots_ax = plt.subplots(
            ncols=subplot_width, 
            nrows=subplot_height,
            tight_layout=True
        )
        # subplots_figure.suptitle('Radar Level Versus Moisture')
        subplots_figure.set_figwidth(40)
        subplots_figure.set_figheight(125)
        subplots_figure.subplots_adjust(top=0.85)
        for line_index, radar_versus_moisture_line in enumerate(radar_versus_moisture_lines):
            sub_ax = subplots_ax[floor(line_index / subplot_width), line_index % subplot_width]
            sub_ax.set_title("Line Number {}".format(line_index + 1), fontsize=10)
            sub_ax.tick_params(axis='both', which='major', labelsize=10)
            sub_ax.plot(
                radar_versus_moisture_line[0], 
                radar_versus_moisture_line[1], 
                linewidth=1
            )
        for line_index in range(line_index + 1, subplot_width * subplot_height):
            sub_ax = subplots_ax[floor(line_index / subplot_width), line_index % subplot_width]
            sub_ax.remove()
            
    plot_radar_versus_moisture_lines(radar_versus_moisture_lines)

    if program_arguments.export_dir is not None:
        plt.savefig(os.path.join(program_arguments.export_dir, "radar_versus_moisture_p={}__individual".format(
            program_arguments.power_levels
        )))
    else:
        plt.show()
