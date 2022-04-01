from html.parser import HTMLParser

import requests

_URL = 'https://www.bgreco.net/garfield/'

class HTTPError(Exception):
    pass

class GarfGenParser(HTMLParser):
    def error(self, message):
        raise HTTPError(message)

    def __init__(self):
        super().__init__()
        self.result = None

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            for name, value in attrs:
                if name == 'href' and value.startswith('save.png'):
                    self.result = _URL + value
                    return

def _test_response(res):
    if res.status_code != 200:
        raise HTTPError(f"Request to {res.url} failed. Status code: {res.status_code}")


def fetch():
    response = requests.get(_URL)
    _test_response(response)
    parser = GarfGenParser()
    parser.feed(response.text)
    img_response = requests.get(parser.result)
    _test_response(img_response)
    return img_response.content
