from __future__ import unicode_literals
import requests
import os
import time
from functools import wraps


API_ENDPOINT = 'https://api.iextrading.com/1.0'
STOCK_ENDPOINT = 'stock/%s'
RED = '\033[91m'
GREEN = '\033[92m'
ENDC = '\033[0m'
MAX_LINE_LENGTH = 70


# EXCEPTIONS
class Error(Exception):
    pass


class InvalidMethod(Error):
    pass


class ResponseError(Error):
    pass


class NoDividends(ResponseError):
    pass


class UnknownSymbol(ResponseError):
    pass


# DECORATORS
def colorize(color):
    def colorize_response(f):
        @wraps(f)
        def colorwrapper(*args, **kwargs):
            response = f(*args, **kwargs)
            colorized = []
            for line in response.splitlines():
                split_line = line.split(':', 1)
                # Do not colorize multi-line text blocks
                if len(split_line) == 1:
                    colorized.append(line)
                    continue
                colorized.append('%s%s%s: %s' % (color, split_line[0], ENDC, split_line[1]))
            return '\n'.join(colorized)
        return colorwrapper
    return colorize_response


def format_response(f):
    @wraps(f)
    def alignwrapper(*args, **kwargs):
        response = f(*args, **kwargs)
        space_length = max([len(line.split(':', 1)[0]) for line in response.splitlines()])
        aligned_text = []
        for line in response.splitlines():
            split_line = line.split(':', 1)
            # Handle text with no header
            if len(split_line) == 1:
                aligned_text.append(line)
                continue
            # Handle multi-line text alignment
            if len(split_line[1]) > MAX_LINE_LENGTH:
                line_text = split_line[1].lstrip()
                num_lines = len(line_text)/MAX_LINE_LENGTH
                aligned_text.append('{0:>{num}}:{1}'.format(split_line[0], line_text[:MAX_LINE_LENGTH],num=space_length+1))
                for i in range(2, num_lines+2):
                    start = MAX_LINE_LENGTH*(i-1)
                    end = MAX_LINE_LENGTH*i
                    aligned_text.append('{0:>{num}}'.format(line_text[start:end].lstrip().replace(':', '-'),
                                                            num=space_length+len(line_text[start:end].lstrip())+3))
            else:
                # Convert numbers to percent if needed
                if 'percent' in split_line[0].lower() and is_float(split_line[1]):
                    aligned_text.append('{0:>{num}}: {1:.0%}'.format(split_line[0], float(split_line[1]),
                                                                     num=space_length))
                # Convert epoch values
                elif split_line[0].lower() == 'time':
                    converted_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(int(split_line[1])/1000))
                    aligned_text.append('{0:>{num}}: {1}'.format(split_line[0], converted_time, num=space_length))
                else:
                    # Add commas to money values
                    if is_float(split_line[1]):
                        aligned_text.append('{0:>{num}}: {1:,}'.format(split_line[0], float(split_line[1]),
                                                                       num=space_length))
                    else:
                        aligned_text.append('{0:>{num}}:{1}'.format(split_line[0], split_line[1], num=space_length))
        return '\n'.join(aligned_text)
    return alignwrapper


# GENERIC FUNCTIONS
def send_get_request(url, session=None):
    """Generic function for sending GET request and handling errors and retries.

    Args:
        url: (str) Address to send the get request to
        session: (requests.session) Session used to maintain cache
    Returns:
        (str) Response from the server

    Raises:
        requests.exceptions.ConnectionError: Raised if we cannot get a response after 3 tries
    """
    retries = 3
    while retries:
        try:
            if session:
                response = session.get(url)
            else:
                response = requests.get(url)
            break
        except requests.exceptions.ConnectionError:
            retries -= 1
            if not retries:
                raise
            time.sleep(1)
    if response.status_code == 404:
        raise UnknownSymbol('Symbol does not exist')
    return response.json()


def is_float(s):
    try:
        float(s)
        return True
    except ValueError:
        return False


# API FUNCTIONS
def get_data(symbol, data_endpoint, sub_key=None):
    url = os.path.join(API_ENDPOINT, STOCK_ENDPOINT % symbol, data_endpoint)
    response = send_get_request(url)
    if not response:
        raise ResponseError('%s has no data for %s.' % (symbol, data_endpoint))
    if sub_key:
        return response[sub_key]
    return response


@colorize(RED)
@format_response
def print_long_response(response):
    print_string = []
    if isinstance(response, list):
        for item in response:
            for key, value in item.iteritems():
                print_string.append('%s: %s' % (key.capitalize(), value))
            print_string.append('='*10)
    else:
        for key, value in response.iteritems():
            print_string.append('%s: %s' % (key.capitalize(), value))
    return '\n'.join(print_string)


def get_user_response(prompt=''):
    response = None
    while not response:
        response = raw_input('%s>> ' % prompt)
    return response


def handle_user_method(user_input):
    user_input_arr = user_input.split()
    requested_method = user_input_arr[0].upper()
    user_method_dict = func_finder(requested_method)
    if not user_method_dict:
        raise InvalidMethod('"%s" function does not exist' % user_input_arr[0])

    if len(user_input_arr) > 1:
        symbol = user_input_arr[1]
    else:
        symbol = get_user_response(requested_method)
    return get_data(symbol, user_method_dict['endpoint'], sub_key=user_method_dict['sub_key'])


def func_finder(method):
    if method.upper() == 'EXIT' or method.upper() == 'Q':
        exit()
    func_dict = {
        'COM': {'endpoint': 'company', 'sub_key': None},
        'DIV': {'endpoint': 'dividends/1y', 'sub_key': None},
        'ER': {'endpoint': 'earnings', 'sub_key': 'earnings'},
        'FIN': {'endpoint': 'financials', 'sub_key': 'financials'},
        # Needs sort by time
        'LTR': {'endpoint': 'largest-trades', 'sub_key': None},
        'NEWS': {'endpoint': 'news', 'sub_key': None},
        'QT': {'endpoint': 'quote', 'sub_key': None}

    }
    return func_dict.get(method.upper(), None)


def main():
    while True:
        try:
            response = handle_user_method(get_user_response())
            print print_long_response(response)
        except InvalidMethod as e:
            print str(e)
        except ResponseError as e:
            print str(e)


if __name__ == '__main__':
    main()
