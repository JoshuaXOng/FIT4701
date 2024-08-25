def is_string_relative_numeric(string):
    if len(string) >= 2 and string[0] in ['-', '+'] and string[1:].isnumeric():
        return True 
    else:
        return False
