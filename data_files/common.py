import os
import pickle
import logging
from data_files.radar_h5 import get_radar_file_start_timestamp, get_radar_file_end_timestamp, get_radar_data_around_timestamp 
from data_files.environments_excel import get_environment_information_start_timestamp, get_environment_information_end_timestamp 

def find_greatest_overlap(radar_file, environment_information):
    radar_start, radar_end = get_radar_file_start_timestamp(radar_file), get_radar_file_end_timestamp(radar_file)
    environment_start, environment_end = get_environment_information_start_timestamp(environment_information), \
        get_environment_information_end_timestamp(environment_information)
    
    logging.info('Radar data starts at... {}, and ends at... {}'.format(radar_start, radar_end)) 
    logging.info('Environment information starts at... {}, and ends at... {}'.format(environment_start, environment_end))
    if radar_start is None  or radar_end is None or environment_start is None or environment_end is None:
        raise Exception('Radar data interval ({} to {}) or environment data ({} to {}) interval based on'
        ' supplied data is in-complete.'.format(radar_start, radar_end, environment_start, environment_end))
    
    latest_start = max(radar_start, environment_start)
    earliest_end = min(radar_end, environment_end)
    return (latest_start, earliest_end)

def join_environment_and_radar_with_tolerance(radar_file, environment_data, join_frequency):
    latest_start, earliest_end = find_greatest_overlap(radar_file, environment_data) 

    environment_and_radar = []
    
    current_timestamp = latest_start
    while current_timestamp <= earliest_end:
        environment_and_radar.append((
            current_timestamp,
            get_radar_data_around_timestamp(radar_file, current_timestamp, join_frequency / 2),
            get_environment_information_around_timestamp(current_timestamp, join_frequency / 2) 
        ))

        current_timestamp += join_frequency 
    
    return environment_and_radar
        
PREPROCESSED_DATA_FILE = 'radar_and_moisture_preprocessed.pkl'
def get_overlap_as_aggregated(radar_file, environment_information):
    latest_start, earliest_end = find_greatest_overlap(radar_file, environment_information) 

    if not os.path.isfile(PREPROCESSED_DATA_FILE):
        radar_and_moisture = []
        for row_index, _environment_information in enumerate(environment_information.iterrows()):   
            logging.debug('At index {} of {}'.format(row_index, environment_information.shape[0]))

            environment_timestamp = _environment_information[1]['TIMESTAMP'] 
            
            if environment_timestamp < latest_start or environment_timestamp > earliest_end:
                logging.debug('Skipping finding corresponding radar data, latest start is... {}, earliest end is... {} and '
                'environment timestamp is... {}'.format(latest_start, earliest_end, environment_timestamp))
                continue
            
            corresponding_radar = get_radar_data_around_timestamp(radar_file, environment_timestamp, datetime.timedelta(seconds=1))
            
            if corresponding_radar is None:
                logging.warning('No corresponding radar data found for environment data of timestamp... {}'.format(environment_timestamp)) 
                continue 
            
            radar_and_moisture.append((_environment_information, corresponding_radar))
        with open(PREPROCESSED_DATA_FILE, 'wb') as save_file:
            pickle.dump(radar_and_moisture, save_file)
            logging.info('Pickled processed radar and moisture to {}.'.format(PREPROCESSED_DATA_FILE))
    else:
        with open(PREPROCESSED_DATA_FILE, 'rb') as save_file:
            radar_and_moisture = pickle.load(save_file)
    
    return radar_and_moisture
