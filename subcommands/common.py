import os
import logging

def validate_arguments_for_radar_file(program_arguments):
    logging.info('Path to radar file is... {}'.format(program_arguments.radar_h5_file))
    if not os.path.isfile(program_arguments.radar_h5_file):
        raise Exception('The path to the radar file does not exist, path was... {}'.format(
            program_arguments.radar_h5_file
        ))
