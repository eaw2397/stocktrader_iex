import requests
import os

API_ENDPOINT = 'https://api.iextrading.com/1.0'
STOCK_ENDPOINT = 'stock/%s'
FAIL = '\033[91m'
ENDC = '\033[0m'


class Error(Exception):
    pass


class InvalidMethod(Error):
    pass


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
    return response.json()


def colorize_response(f):
    response = f(*args, **kwargs)
    colorized = []
    for line in response.splitlines():
        split_line = line.split(':', 1)
        colorized.append('%s%s%s: %s' % (FAIL, split_line[0], ENDC, split_line[1]))
    return '\n'.join(colorized)


@colorize_response
def print_long_response(response):
    print_string = []
    for key, value in response.iteritems():
        print_string.append('%s: %s' % (key.capitalize(), value))
    return '\n'.join(print_string)


def get_user_response(prompt=''):
    response = None
    while not response:
        response = raw_input('%s >> ' % prompt)
    return response


def get_company_data(symbol):
    url = os.path.join(API_ENDPOINT, STOCK_ENDPOINT % symbol, 'company')
    response = send_get_request(url)
    return response


def handle_user_method(user_input):
    user_input_arr = user_input.split()
    requested_method = user_input_arr[0]
    user_method = f(requested_method)
    if not user_method:
        raise InvalidMethod('"%s" function does not exist' % user_input_arr[0])

    if len(user_input_arr) > 1:
        symbol = user_input_arr[1]
        return user_method(symbol)
    else:
        symbol = get_user_response(requested_method)
        return user_method(symbol)


def f(method):
    if method.upper() == 'EXIT':
        exit()
    func_dict = {
        'COM': get_company_data
    }
    return func_dict.get(method.upper(), None)


def main():
    while True:
        try:
            response = handle_user_method(get_user_response())
            print_long_response(response)
        except InvalidMethod as e:
            print str(e)
            pass

if __name__ == '__main__':
    main()
