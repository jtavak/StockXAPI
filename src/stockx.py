import json
from datetime import datetime
import requests
import base64
from bs4 import BeautifulSoup


class StockXAPI:
    def __init__(self):
        self.client_id = ''
        self.token = ''

    def _process_json(self, json_data, output_data):
        return_data = [i for i in output_data if type(i) == str]
        secondary_return_data = [i for i in output_data if type(i) == list]

        product_data = {}

        for key in return_data:
            if key in json_data:
                product_data[key] = json_data[key]

        for top_key, bottom_key in secondary_return_data:
            for key in json_data[top_key]:
                if key == bottom_key:
                    product_data[bottom_key] = json_data[top_key][bottom_key]

        return product_data

    def _get_login_info(self):
        url='https://stockx.com/login'
        headers = {'content-type': 'application/json',
                   'cookie': '_csrf=vlM3ad_qXdZhY1orZPZ7oOxO;',
                   'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_2)'
                                 ' AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.88 Safari/537.36'}

        resp = requests.get(url, headers=headers)

        cookie_headers = resp.headers['Set-Cookie']
        cookie_csrf_end = cookie_headers.find(';') + 1
        cookie_csrf = cookie_headers[:cookie_csrf_end]

        soup = BeautifulSoup(resp.content, 'html.parser')
        script_content = str(soup.body.find_all('script')[5])

        config_start = script_content.find('window.atob') + 13
        config_end = script_content.find("'))));")

        config_data = script_content[config_start:config_end]

        output = json.loads(base64.b64decode(config_data))
        client_id = output['clientID']
        data_csrf = output['internalOptions']['_csrf']

        self.client_id = client_id
        return cookie_csrf, data_csrf

    def login(self, username, password):
        """
        Logs into StockX with username and password and sets self.token to the authentication token.
        :param username: Account username.
        :param password: Account password.
        :return: None.
        """
        login_url = 'https://accounts.stockx.com/usernamepassword/login'

        cookie_csrf, data_csrf = self._get_login_info()

        login_headers = {'content-type': 'application/json',
                         'cookie': cookie_csrf,
                         'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_2)'
                                       ' AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.88 Safari/537.36'}

        login_data = {'client_id': self.client_id,
                      'tenant': 'stockx-prod',
                      '_csrf': data_csrf,
                      'username': username,
                      'password': password,
                      'connection': 'production'}
        
        resp = requests.post(login_url, headers=login_headers, json=login_data)
        soup = BeautifulSoup(resp.content, 'html.parser')
        token = soup.find('input', {'name': 'wresult'})['value']

        self.token = token

    def search_items(self, search_term, output_data=None, page=1, max_searches=-1):
        """
        Searches a term on StockX using the browse API function.
        :param search_term: Term to search for on StockX.
        :param output_data: Which pieces of data from the JSON string to return eg. name, id, category, brand, year or
        [market, lastSale], [market, lowestAsk], [media, imageURL].
        :param page: Which page of products to search on.
        :param max_searches: How many items to search for.
        :return: Returns a list containing dictionaries of data specified in output_data
        """
        if output_data is None:
            output_data = ['name']
        search_term = search_term.replace(' ', '%20')
        url = 'https://stockx.com/api/browse?&page={}&_search={}&dataType=product&country=US'.format(page, search_term)

        user_agent = {'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_2) AppleWebKit/537.36'
                                    ' (KHTML, like Gecko) Chrome/79.0.3945.88 Safari/537.36'}

        resp = requests.get(url, headers=user_agent)
        data = json.loads(resp.content)['Products'][:max_searches]

        final_data = []
        for item in data:
            final_data.append(self._process_json(item, output_data))

        return final_data

    def get_item_data(self, item_id, output_data=None):
        """
        Gets data for individual items using the StockX product API function.
        :param item_id: id, uuid, productUuid or urlKey of the item to get data on.
        :param output_data: Which pieces of data from the JSON string to return eg. name, id, category, brand, year or
        [market, lastSale], [market, lowestAsk], [media, imageURL].
        :return: Returns a dictionary of values specified in output_data.
        """
        if output_data is None:
            output_data = ['name']

        url = 'https://stockx.com/api/products/{}'.format(item_id)

        user_agent = {'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_2) AppleWebKit/537.36'
                                    ' (KHTML, like Gecko) Chrome/79.0.3945.88 Safari/537.36'}
        resp = requests.get(url, headers=user_agent)

        data = json.loads(resp.content)['Product']

        market_data_url = 'https://stockx.com/api/products/{}/market'.format(item_id)
        resp = requests.get(market_data_url, headers=user_agent)
        market_data = json.loads(resp.content)['Market']

        data['market'] = market_data
        final_data = self._process_json(data, output_data)
        return final_data

    def get_past_prices(self, item_id, start_date='all', end_date=None, data_points=100):
        """
        Get the sale prices of an item over time.
        :param item_id: Id of item to use.
        :param start_date: When to start the data, use all for all time.
        :param data_points: How many points to return
        :return: Lists with x and y values of price data
        """
        url = 'https://stockx.com/api/products/{}/chart?start_date={}&end_date={}' \
              '&intervals={}&format=highstock&currency=USD&country=US'.format(item_id, start_date, end_date,
                                                                              data_points)

        user_agent = {'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_2) AppleWebKit/537.36'
                                    ' (KHTML, like Gecko) Chrome/79.0.3945.88 Safari/537.36'}

        resp = requests.get(url, headers=user_agent)
        data = json.loads(resp.content)['series'][0]['data']

        x = []
        y = []

        for timestamp, price in data:
            x.append(datetime.fromtimestamp(int(timestamp / 1000)))
            y.append(price)

        return x, y
