import json
import ssl
import bs4
import pymongo
import requests
import atexit
from bson.json_util import dumps
from flask import request, Flask, jsonify
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from flask_cors import CORS

app = Flask(__name__)
CORS(app)
client = pymongo.MongoClient("mongodb+srv://nadatade:nadatade123@cluster0.3cow8.mongodb.net/test2?retryWrites=true&w=majority",ssl_cert_reqs=ssl.CERT_NONE)
db = client.test
mydatabase = client["test2"]
mycollection = mydatabase["testtable2"]


def crawl():
    url = "https://www.statista.com/statistics/1103458/india-novel-coronavirus-covid-19-cases-by-state/"  # "https://www.mohfw.gov.in/"
    response = requests.get(url)

    soup_object = bs4.BeautifulSoup(response.text, "html.parser")
    my_table_tag = soup_object.select("table")
    mytable = my_table_tag[0]
    my_table_rows = mytable.find_all('tr')

    for i in range(1, len(my_table_rows)):
        state = my_table_rows[i].find_all('td')[0].get_text().replace('\r', "")
        active = my_table_rows[i].find_all('td')[1].get_text().replace(',', "")
        safe = my_table_rows[i].find_all('td')[2].get_text().replace(',', "")
        deaths = my_table_rows[i].find_all('td')[3].get_text().replace(',', "")
        date_stamp = datetime.now().date()
        print(str(state))
        # check for duplicates
        check_duplicates_query = {"date_stamp": str(date_stamp), "state": state}
        duplicates = mycollection.find(check_duplicates_query)

        # if no duplicates
        if duplicates.count() == 0:
            insert_data = {"date_stamp": str(date_stamp),
                           "state": state,
                           "positive_cases": active,
                           "recovered": safe,
                           "deaths": deaths
                           }
            mycollection.insert_one(insert_data)
            print("added new data")

        else:
            data = list(duplicates)
            data_json = json.loads(dumps(data[0]))

            if (int(data_json["positive_cases"]) != int(active)):
                new_value = {"$set": {"positive_cases": active}}
                mycollection.update(check_duplicates_query, new_value)
                print("found an updated value while crawling hence updated")

            if (int(data_json["recovered"]) != int(safe)):
                new_value = {"$set": {"recovered": safe}}
                mycollection.update(check_duplicates_query, new_value)
                print("found an updated value while crawling hence updated")

            if (int(data_json["deaths"]) != int(deaths)):
                new_value = {"$set": {"deaths": deaths}}
                mycollection.update(check_duplicates_query, new_value)
                print("found an updated value while crawling hence updated")
            print("nothing to update")

#returns data of a particular state
@app.route("/getcurrentdataforstate")
def getcurrentdataforstate():
    state = request.args.get('state', type=str)
    query = {"state": state}
    data = mycollection.find(query, {"_id": 0})
    listdata = list(data)
    length = len(listdata)
    return jsonify(listdata[length-1])

#returns history of a particular state
@app.route("/getstatehistory")
def getstatehistory():
    state = request.args.get('state', type=str)
    query = {"state": state}
    data = mycollection.find(query, {"_id": 0})
    listdata = list(data)
    return jsonify(listdata)

#returns data of all the states
@app.route("/getallstatesforcurrentdate")
def getallstatesforcurrentdate():
    date_stamp = datetime.now().date()
    query = {"date_stamp": str(date_stamp)}
    data = mycollection.find(query, {"_id": 0})
    returndata = list(data)
    return jsonify(returndata)

#returns all the states
@app.route("/getstatenames")
def getstatenames():
    states="Maharashtra,Tamil Nadu,Karnataka,Delhi,Andhra Pradesh,Uttar Pradesh,Telangana,Gujarat,West Bengal,Rajasthan,Assam,Bihar,Haryana,Jammu and Kashmir,Odisha,Madhya Pradesh,Kerala,Punjab,Jharkhand,Goa,Chhattisgarh,Manipur,Uttarakhand,Puducherry,Tripura,Nagaland,Himachal Pradesh,Meghalaya,Dadra and Nagar Haveli and Daman and Diu,Arunachal Pradesh,Ladakh,Chandigarh,Mizoram,Sikkim,Andaman and Nicobar Islands"
    return str(states)
#W
@app.route("/add")
def add():
    return str("success")

@app.route("/getstatehistoryforrange")
def getstatehistoryforrange():
    date_stamp = datetime.now().date()
    state = request.args.get('state',type=str)
    range = request.args.get('range',type=int)
    date_neede_query = date_stamp-timedelta(days=range)
    query={"state":state,"date_stamp":{"$gt":str(date_neede_query)}}
    data=mycollection.find(query,{"_id":0})
    querydata=list(data)
    return jsonify(querydata)

#returns total cases for all states
@app.route("/totalcases")
def totalcase():
    date_stamp = datetime.now().date()
    query = {"date_stamp": str(date_stamp)}
    data = mycollection.find(query)
    total_pc = 0
    total_sf = 0
    total_d = 0
    total_data = {}
    for state in data:
        jsondata = json.loads(dumps(state))
        total_pc += int(str(jsondata["positive_cases"]).replace(',', ''))
        total_sf += int(str(jsondata["recovered"]).replace(',', ''))
        total_d += int(str(jsondata["deaths"]).replace(',', ''))

    total_data = {
        "total_positive": total_pc,
        "total_recovered": total_sf,
        "total_deaths": total_d
    }
    return total_data


scheduler = BackgroundScheduler()
scheduler.add_job(func=crawl, trigger="interval", seconds=3000)
scheduler.start()

atexit.register(lambda: scheduler.shutdown())
if __name__ == '__main__':
    app.run()
