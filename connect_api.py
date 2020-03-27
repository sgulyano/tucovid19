import requests
import json
import os

headers = { os.environ['KEY'] : os.environ['TOKEN']}

apis = ['user', 'Daily']

for api in apis:
    resp = requests.get('https://restapi.tu.ac.th/tu_covid_api/v1/master/{}/getdata'.format(api), headers=headers)
    if resp.status_code != 200:
        # This means something went wrong.
        raise ApiError('GET /{}/ {}'.format(api, resp.status_code))

    with open('{}.json'.format(api), 'w', encoding='utf-8') as f:
        json.dump(resp.json(), f, ensure_ascii=False, indent=4)
    print('GET /{}/ {} OK'.format(api, resp.status_code))