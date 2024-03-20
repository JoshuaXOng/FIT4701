import datetime
import bisect

def reoriente_sensor_data(sensors_data):
    return sensors_data.swapaxes(0, 1)[:][0].swapaxes(0, 1)

def get_radar_file_start_timestamp(radar_file):
    return datetime.datetime.fromtimestamp(
        min(radar_file['sample_times'][:])
    ) 

def get_radar_file_end_timestamp(radar_file):
    return datetime.datetime.fromtimestamp(
        max(radar_file['sample_times'][:])
    ) 

def get_radar_data_around_timestamp(radar_file, center_datetime, leniency_timedelta):
    if radar_file['sample_times'].shape[0] != radar_file['data'].shape[0]:
        logging.warning('Data and timestamps are not of the same length.')
    
    radar_timestamps = list(map(lambda x: datetime.datetime.fromtimestamp(x), radar_file['sample_times'][:]))
    candidate_indices = [bisect.bisect_left(radar_timestamps, center_datetime),
        bisect.bisect_right(radar_timestamps, center_datetime)]
    get_delta = lambda x: abs((center_datetime - x).total_seconds())
    candidate_index = min(candidate_indices, key=lambda x: get_delta(radar_timestamps[x]))
    if get_delta(radar_timestamps[candidate_index]) \
    >= leniency_timedelta.total_seconds():
        return None

    return radar_file['data'][candidate_index]
