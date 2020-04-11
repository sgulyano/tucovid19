import requests
import json
import os
import pandas as pd
import time
from datetime import datetime, timedelta
from neo4j import GraphDatabase, exceptions

print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

headers = { os.environ['KEY'] : os.environ['TOKEN']}
    
def load_data_from_api(api, headers = headers):
    try:
        resp = requests.get('https://restapi.tu.ac.th/tu_covid_api/v1/master/{}/getdata'.format(api), headers=headers)
        if resp.status_code != 200:
            # This means something went wrong.
            raise requests.RequestException('GET /{}/ {}'.format(api, resp.status_code))

        print('GET /{}/ {} OK'.format(api, resp.status_code))
        return resp.json()
    except Exception as e:
        time.sleep(1)
        return load_data_from_api(api)

# get data in json format from API
json_user = load_data_from_api('user')
json_daily = load_data_from_api('Rick')
json_risk = load_data_from_api('Daily')
json_loc = load_data_from_api('Location')

# load into DataFrame
patients = pd.DataFrame(json_user['data'], dtype='object')
patients['IsMedStaff'] = patients['MedicalStaff'].apply(lambda x: x == 'บุคลากรทางการแพทย์')
dailyforms = pd.DataFrame(json_daily['data'])
dailyforms.rename(columns={'CREATE_DATE_CONVERT': 'Create_date'}, inplace=True)
riskforms = pd.DataFrame(json_risk['data'])
locforms = pd.DataFrame(json_loc['data'])

# handle datetime of location forms
def get_date_time(row):
    if row['formLocationDate'] and row['formLocationTime']:
        date_time_str = row['formLocationDate'] + ' ' + row['formLocationTime']
        return datetime.strptime(date_time_str, '%Y-%m-%d %H:%M')
    else:
        return None

locforms['start'] = locforms.apply(get_date_time, axis=1)
locforms['end'] = locforms['start'].apply(lambda x: x + timedelta(hours=4))
locforms['start'] = locforms['start'].apply(str)
locforms['end'] = locforms['end'].apply(str)
locforms.replace({'NaT': '-'}, inplace=True)
locforms.fillna('-', inplace=True)

# connect Neo4j
uri = "bolt://localhost:7687"
driver = GraphDatabase.driver(uri, auth=(os.environ['NEO4J_USERNAME'], os.environ['NEO4J_PASSWORD']), encrypted=False)

# add nodes
try:
    with driver.session() as session:
        session.run("""CREATE CONSTRAINT unique_username
                    ON (n:Person) 
                    ASSERT n.username IS UNIQUE""")
except:
    pass

def create_person(driver, param):
    try:
        with driver.session() as session:
            return session.run("""CREATE (a:Person {username:$Username, 
                                                    type:$Type,
                                                    age:$Age,
                                                    org:$OrgCompany,
                                                    emptype:$EmpType,
                                                    gender:$Gender,
                                                    blood:$Blood,
                                                    ismedstaff:$IsMedStaff,
                                                    bloodres:$BloodResults,
                                                    home:$Home,
                                                    province:$Provice
                                                   })""", param)
    except exceptions.ConstraintError:
        return None

for index, row in patients.iterrows():
    create_person(driver, row.to_dict())

# add color attribute to nodes
def convert_str_date(s):
    return datetime.strptime(s, '%Y-%m-%d')

COLOR_MAP = {'สีเขียว':0, 'สีเหลือง':1, 'สีแดง':4, 'สีส้ม':3, 'สีน้ำเงิน':2, 'สีม่วง':5}

def update_color(driver, param, DATE_THR=timedelta(days=14)):
    with driver.session() as session:
        tx = session.begin_transaction()
        rec = tx.run("MATCH (a:Person {username:$Username } ) "
                    "RETURN id(a), a.username, a.color, a.color_date", param).single()
        if rec:
            needUpdate = True
            if rec['a.color'] and rec['a.color_date']:    
                # if new value has higher color level
                if (COLOR_MAP[rec['a.color']] < COLOR_MAP[param['COLOR']]):
                    # check if new value create date is less than threshold
                    if datetime.now() - convert_str_date(param['Create_date']) < DATE_THR:
                        needUpdate = True
                    else:
                        needUpdate = False
                # to reduce level, must pass date threshold and new date is greater
                elif (COLOR_MAP[rec['a.color']] > COLOR_MAP[param['COLOR']]):
                    if convert_str_date(param['Create_date']) - convert_str_date(rec['a.color_date']) > DATE_THR and \
                            convert_str_date(rec['a.color_date']) < convert_str_date(param['Create_date']):
                        needUpdate = True
                    else:
                        needUpdate = False
                # if equal level, do nothing (assume data are sorted before hand)
                else:
                    needUpdate = False
                
                if needUpdate:
                    print(f"{rec['id(a)']} update {rec['a.color']:10s} --> {param['COLOR']}")
                    print('\t', rec['a.color_date'], ' \t ', param['Create_date'])
                
            if needUpdate:
                tx.run("MATCH (a:Person {username:$Username } ) "
                       "SET a.color = $COLOR, a.color_date = $Create_date ", param)             
        else:
            raise Exception('No Node with the Name : ', param['Username'])
        tx.commit()
        return rec


color_info = pd.concat([riskforms[['Username', 'LineID', 'COLOR', 'Create_date']], 
                        dailyforms[['Username', 'LineID', 'COLOR', 'Create_date']]], axis=0).sort_values(by=['Create_date']).reset_index()

for index, row in color_info.iterrows():
    try:
        update_color(driver, row.to_dict())
    except Exception as e:
        print(e)

# create edges
def create_went_to_location(driver, param):
    with driver.session() as session:
        session.run("MERGE (b:Location {title:$messageTitle, lat:$messageLatitude, lon:$messageLongitude, address:$messageAddress})", param)
        session.run("""MATCH (a:Person {username:$Username } )
                       MATCH (b:Location {title:$messageTitle, lat:$messageLatitude, lon:$messageLongitude, address:$messageAddress})
                       MERGE (a)-[r:WENT_TO {activity:$formLocationDetail, start:$start, end:$end}]->(b);""", param)

for index, row in locforms.iterrows():
    create_went_to_location(driver, row.to_dict())

# put time stamp
with driver.session() as session:
    rec = session.run("MATCH (a:UpdateTime)  RETURN a.updatetime").single()
    if rec:
        session.run("MATCH (a:UpdateTime)  SET a.updatetime = $updatetime", {'updatetime':datetime.now().strftime('%Y-%m-%d %H:%M:%S')})
    else:
        session.run("CREATE (a:UpdateTime {updatetime:$updatetime})", {'updatetime':datetime.now().strftime('%Y-%m-%d %H:%M:%S')})
        