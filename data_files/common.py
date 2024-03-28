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
        
