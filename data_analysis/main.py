import sys
import os
import logging
import datetime
import itertools
import argparse
from subcommands.plot import attach_plot_subcommand 
from subcommands.model import attach_model_subcommand 

def main():
    root_argument_parser = argparse.ArgumentParser()
    root_argument_parser.add_argument('-l', '--log_level')
    def root_function(program_arguments):
        root_argument_parser.print_help()
    root_argument_parser.set_defaults(func=root_function)
    root_subcommands = root_argument_parser.add_subparsers(
        title='subcommands'
    )

    attach_plot_subcommand(root_subcommands),
    attach_model_subcommand(root_subcommands)

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

    program_arguments.func(program_arguments)

if __name__ == '__main__':
    main()
