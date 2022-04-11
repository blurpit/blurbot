from html.parser import HTMLParser

import requests


class HTTPError(Exception):
    pass

class GarfGenParser(HTMLParser):
    def __init__(self, url):
        super().__init__()
        self.url = url
        self.result = None

    def error(self, message):
        raise HTTPError(message)

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            for name, value in attrs:
                if name == 'href' and value.startswith('save.png'):
                    self.result = self.url + value
                    return

def _verify_response(res):
    if res.status_code != 200:
        raise HTTPError('Request to {} failed. Status code: {}'.format(res.url, res.status_code))


def fetch(url):
    response = requests.get(url)
    _verify_response(response)
    parser = GarfGenParser(url)
    parser.feed(response.text)
    img_response = requests.get(parser.result)
    _verify_response(img_response)
    return img_response.content
