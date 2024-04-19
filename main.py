import sys
import os
import logging
import datetime
import itertools
import argparse
from subcommands.plot import run_plot_subcommand
from subcommands.versus import run_versus_subcommand 
from subcommands.pca import run_pca_subcommand 
from subcommands.model import run_model_subcommand 

def main():
    root_argument_parser = argparse.ArgumentParser()
    root_argument_parser.add_argument('-l', '--log_level')
    def root_command(program_arguments):
        root_argument_parser.print_help()
    root_argument_parser.set_defaults(func=root_command)
    root_subcommands = root_argument_parser.add_subparsers(
        title='subcommands'
    )

    def _():
        plot_parser = root_subcommands.add_parser('plot')
        plot_parser.add_argument('-r', '--radar_h5_file', 
            help='Path to the h5 radar file.')
        plot_parser.add_argument('-e', '--environment_file',
            help='Path to the csv that contains the moisture data.')
        plot_parser.add_argument('-i', '--initial_region', 
            help='Slice of initial viewing region of radar data, e.g., '
            'can exclude or set like \'3000,400\' (no relative start)')
        plot_parser.set_defaults(func=run_plot_subcommand)
        plot_subcommands = plot_parser.add_subparsers(title='subcommands')

        versus_parser = plot_subcommands.add_parser('versus')
        versus_parser.set_defaults(func=run_versus_subcommand)

        pca_parser = plot_subcommands.add_parser('pca')
        plot_parser.add_argument('-p', '--power-level', 
            help='Whether or not, and to determine which levels of power'
            'to plot.')
        pca_parser.set_defaults(func=run_pca_subcommand)
    _()

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

    program_arguments = root_argument_parser.parse_args()
        
    if program_arguments.log_level is None:
        program_arguments.log_level = logging.INFO
    try:
        program_arguments.log_level = int(program_arguments.log_level)
    except Exception as e:
        raise Exception('Log level should be an integer, '
        'was... {}'.format(program_arguments.log_level))
    logging.basicConfig(level=program_arguments.log_level, format='%(asctime)s '
    '- %(name)s - %(levelname)s - %(message)s')
    
    # TODO: Validate and dispatch from commands here
    # if program_arguments.func is run_plot_subcommand:
    #    program_arguments.func(program_arguments.environment_file) 

    program_arguments.func(program_arguments)

if __name__ == '__main__':
    main()
