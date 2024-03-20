import datetime

def environment_timestamp_to_datetime(environment_timestamp):
    return datetime.datetime.strptime(environment_timestamp, "%m/%d/%y %H:%M")

def get_environment_information_start_timestamp(environment_information):
    return min(environment_information.iloc[:, 0])

def get_environment_information_end_timestamp(environment_information):
    return max(environment_information.iloc[:, 0])

def get_environment_information_around_timestamp(environment_information, center_datetime, leniency_timedelta):
    closest_row, smallest_timedelta = None, None
    for row_information in environment_information.iterrows():      
        row_timestamp = row_information[1]['TIMESTAMP'] 
        candidate_timedelta = center_datetime - row_timestamp
        if abs(candidate_timedelta.total_seconds()) < leniency_timedelta.total_seconds():
            if (closest_row is None and smallest_timedelta is None) \
            or (abs(candidate_timedelta.total_seconds()) < smallest_timedelta.total_seconds()):
                closest_row, smallest_timedelta = row_information, candidate_timedelta
    return closest_row
