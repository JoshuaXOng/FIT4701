import os
import logging

def validate_arguments_for_radar_file(program_arguments):
    logging.info('Path to radar file is... {}'.format(program_arguments.radar_h5_file))
    if not os.path.isfile(program_arguments.radar_h5_file):
        raise Exception('The path to the radar file does not exist, path was... {}'.format(
            program_arguments.radar_h5_file
        ))

def validate_arguments_for_environments_file(program_arguments):
    logging.info('Path to environments file is... {}'.format(program_arguments.environment_file)) 
    if program_arguments.environment_file is None or not os.path.isfile(program_arguments.environment_file):
        raise Exception('Path to environments file does not point to a real file, was... {}'
        .format(program_arguments.environment_file))
