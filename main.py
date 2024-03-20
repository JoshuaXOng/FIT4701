import sys
import os
import logging
import datetime
import itertools
import argparse
from subcommands.plot import run_plot_subcommand
from subcommands.model import run_model_subcommand 

def main():
    argument_parser = argparse.ArgumentParser()
    argument_parser.add_argument('-l', '--log_level')
    subcommand_parsers = argument_parser.add_subparsers(
        title='subcommands'
    )

    plot_parser = subcommand_parsers.add_parser('plot')
    plot_parser.add_argument('-r', '--radar_h5_file', 
        help='Path to the h5 radar file.')
    plot_parser.add_argument('-i', '--initial_region', 
        help='Slice of initial viewing region of radar data, e.g., '
        'can exclude or set like \'3000,400\' (no relative start)')
    plot_parser.set_defaults(func=run_plot_subcommand)

    model_parser = subcommand_parsers.add_parser('model')
    model_parser.add_argument('-r', '--radar_h5_file', 
        help='Path to the h5 radar file.')
    model_parser.add_argument('-e', '--environment_file',
        help='Path to the csv that contains the moisture data.')
    model_parser.add_argument('-g', '--guess_for',
        help='Path to a file containing radar data to be fed to the model.')
    model_parser.add_argument('-m', '--model',
        help='Path to a file containing the model.')
    model_parser.set_defaults(func=run_model_subcommand)

    program_arguments = argument_parser.parse_args()
    if program_arguments.log_level is None:
        program_arguments.log_level = logging.INFO
    try:
        program_arguments.log_level = int(program_arguments.log_level)
    except Exception as e:
        raise Exception('Log level should be an integer, '
        'was... {}'.format(program_arguments.log_level))
    logging.basicConfig(level=program_arguments.log_level, format='%(asctime)s '
    '- %(name)s - %(levelname)s - %(message)s')
    program_arguments.func(program_arguments)

if __name__ == '__main__':
    main()
