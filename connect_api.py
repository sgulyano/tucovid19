import requests
import json
import os
from datetime import date

today = date.today()

headers = { os.environ['KEY'] : os.environ['TOKEN']}

apis = ['user', 'Rick', 'Daily', 'Location']

for api in apis:
    if not os.path.exists('./json/{}_{}.json'.format(api, today)):
        try:
            resp = requests.get('https://restapi.tu.ac.th/tu_covid_api/v1/master/{}/getdata'.format(api), headers=headers)
            if resp.status_code != 200:
                # This means something went wrong.
                raise requests.RequestException('GET /{}/ {}'.format(api, resp.status_code))

            with open('./json/{}_{}.json'.format(api, today), 'w', encoding='utf-8') as f:
                json.dump(resp.json(), f, ensure_ascii=False, indent=4)
            print('GET /{}/ {} OK'.format(api, resp.status_code))
        except Exception as e:
            print(e)