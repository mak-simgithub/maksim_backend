from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Union, Dict
from pydantic import BaseModel
import sqlite3
from dateutil import parser, tz
import datetime
import time
from astral import LocationInfo
from astral.sun import sun
import math
import threading

db_connection = sqlite3.connect("maksim.db")

db_cursor = db_connection.cursor()

db_connection.execute('''CREATE TABLE IF NOT EXISTS parameter_names
         (ID INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
         name TEXT NOT NULL,
         value REAL,
         timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP);''')

param_names_farm = ["farm_light",
                "pump_state",
                "farm_light_off_time",
                "alarm_mon_time",
                "alarm_mon_state",
                "alarm_tue_time",
                "alarm_tue_state",
                "alarm_wed_time",
                "alarm_wed_state",
                "alarm_thu_time", 
                "alarm_thu_state",
                "alarm_fri_time", 
                "alarm_fri_state",
                "alarm_sat_time", 
                "alarm_sat_state",
                "alarm_sun_time", 
                "alarm_sun_state",
                "watering_period", 
                "watering_duration", 
                "last_esp_contact"]

param_names_all = param_names_farm

db_connection.execute('''CREATE TABLE IF NOT EXISTS parameter_values
         (ID INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
         type INTEGER NOT NULL,
         value REAL NOT NULL,
         timestamp TEXT);''')


for param in param_names_all:
    db_cursor.execute(f"SELECT ID FROM parameter_names WHERE name = '{param}';")
    result = db_cursor.fetchall()
    if not len(result):
        print(f"entering dummy data for parameter {param}")
        db_cursor.execute(f"INSERT INTO parameter_names (name, value) VALUES ('{param}', 0);")

db_cursor.execute("SELECT * FROM parameter_names;")

print("Content of parameter_names:")

for row in db_cursor:
    print(row)

db_connection.commit()
db_connection.close()


def insert_to_db(name, value, db_connection, db_cursor):
    now = datetime.datetime.now()
    selectstring = f"SELECT id FROM parameter_names WHERE name is '{name}';"
    db_cursor.execute(selectstring)
    id = db_cursor.fetchone()[0]

    updatestring_names = f"UPDATE parameter_names SET value = {value}, timestamp = '{now}' WHERE id = {id};"
    db_cursor.execute(updatestring_names)

    inserstring_values = f"INSERT INTO parameter_values (type, value, timestamp) VALUES (?,?,?);"
    values_values = (id, value, now)
    db_cursor.execute(inserstring_values,values_values)

    db_connection.commit()


def get_from_db(name, db_cursor):
    selectstring = f"SELECT value FROM parameter_names WHERE name = '{name}';"
    db_cursor.execute(selectstring)
    return db_cursor.fetchone()[0]

def number_to_time(time_number):
    number_string = f"{int(time_number)}"
    if (len(number_string) < 2):
        number_string_parsed = "00:0" + number_string
    elif (len(number_string) < 3):
        number_string_parsed = "00:" + number_string
    elif (len(number_string) < 4):
        number_string_parsed = "0" + number_string[0] + ":" + number_string[1:3]
    else:
        number_string_parsed = number_string[0:2] + ":" + number_string[2:4]
    return number_string_parsed


def time_to_number(time):
    number = int(time.split(":")[0])*100+int(time.split(":")[1])
    return number

app = FastAPI()

app.type = "00"

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def create_db_connection():
    db_connection = sqlite3.connect("maksim.db")
    db_cursor = db_connection.cursor()
    return [db_cursor, db_connection]


@app.get("/farm_params")
async def get_farm_params():
    [db_cursor, db_connection] = create_db_connection()

    param_names_string = f"{param_names_farm}"[1:-1]
    selectstring = f"SELECT name, value, timestamp FROM parameter_names WHERE name IN ({param_names_string});"

    try:
       db_cursor.execute(selectstring)
       params = {}
       for row in db_cursor:
           if "time" in row[0]:
               params[row[0]] = {"value": number_to_time(row[1]), "timestamp": row[2]}
           else:
               params[row[0]] = {"value": row[1], "timestamp": row[2]}

       return {"params": params}

    except Exception as e:
        raise
    finally:
        db_connection.close()

@app.get("/turn_pump_on/{seconds}")
async def turn_pump_on(seconds: int):
    [db_cursor, db_connection] = create_db_connection()
    insert_to_db("pump_state", 1023, db_connection, db_cursor)
    print(f"turning pump on for {seconds}s")
    t = threading.Thread(target=turn_off, args=(seconds,))
    t.start()
    return {"done": 1}

def turn_off(seconds):
    print(f"wait {seconds}")
    time.sleep(seconds)
    print("off")
    [db_cursor, db_connection] = create_db_connection()
    insert_to_db("pump_state", 0, db_connection, db_cursor)



class Param_dict(BaseModel):
    params: Dict[str, Union[float, str]]


@app.post("/params")
async def write_params(param_dict: Param_dict):
    [db_cursor, db_connection] = create_db_connection()
    param_dict_py = param_dict.params

    print("Writing parameters:")
    print(param_dict_py)

    now = datetime.datetime.now().astimezone(tz.tzutc()).isoformat()

    try:
       for key, value in param_dict_py.items():
           if "time" in key:
               value = time_to_number(value)
           
           insert_to_db(key, value, db_connection, db_cursor)

       return {"status": 1}


    except Exception as e:
        raise e
    finally:
        db_connection.close()



@app.get("/farm_params_esp", response_class=PlainTextResponse)
async def get_farm_params_esp():
    [db_cursor, db_connection] = create_db_connection()

    #get light

    light_db = get_from_db("farm_light", db_cursor)

    farm_light_off_time = get_from_db("farm_light_off_time", db_cursor)

    now = datetime.datetime.now()
    #now = now.replace(hour=22, minute=45)
    print(f"it is {now}")

    time_number = int(f"{int(farm_light_off_time)}")
    if time_number < 100:
        hour = 0
        minute = time_number
    else:
        hour = int(time_number/100)
        minute = time_number%100
    farm_light_off_time = now.replace(hour=hour, minute = minute)

    duration_transitions_minute = 30

    day_translate = {
                        0: "mon",
                        1: "tue",
                        2: "wed",
                        3: "thu",
                        4: "fri",
                        5: "sat",
                        6: "sun",
                        }


    day = day_translate[now.weekday()]

    alarm_state = get_from_db(f"alarm_{day}_state", db_cursor)

    alarm_time = get_from_db(f"alarm_{day}_time", db_cursor)

    time_number = int(f"{int(alarm_time)}")
    if time_number < 100:
        hour = 0
        minute = time_number
    else:
        hour = int(time_number/100)
        minute = time_number%100
    wakeup = now.replace(hour=hour, minute = minute)
        
    city = LocationInfo("Zurich")
    s = sun(city.observer, date=now)

    sunrise = s['dawn'].replace(tzinfo=None)
    sunset = s['dusk'].replace(tzinfo=None)


    start_time_lightrise = wakeup-datetime.timedelta(minutes = duration_transitions_minute)
    start_time_sunrise = sunrise-datetime.timedelta(minutes = duration_transitions_minute)
    start_time_sunset = sunset-datetime.timedelta(minutes = duration_transitions_minute)
    start_time_lightset = farm_light_off_time-datetime.timedelta(minutes = duration_transitions_minute)


    is_lightrise = (start_time_lightrise-now).total_seconds()/60<duration_transitions_minute and alarm_state
    is_sunrise = (start_time_sunrise-now).total_seconds()/60<duration_transitions_minute
    is_sunset = (start_time_sunset-now).total_seconds()/60<duration_transitions_minute
    is_lightset = (start_time_lightset-now).total_seconds()/60<duration_transitions_minute


    print(f"light db: {bool(light_db)}")

    #if light not 0, light is set to value
    #if light not 0 during lightset, light gets dimmed and value set to 0
    #if light not 0 during lightsetch after first minute, light is set to value

    #if light is 0, lightrise then lightset_sunrise if necessary, then lightrise_sunset
    print("")
    if not light_db:
        light = 0
        print(f"start lightrise: {start_time_lightrise}")
        print(f"lightrise: {is_lightrise}, light coming on")
        if is_lightrise:
            light = (now-start_time_lightrise).total_seconds()/(60*duration_transitions_minute)*1023
            if light > 1500:
                light = 0
            print(f"progress lightrise: {(now-start_time_lightrise).total_seconds()/(60*duration_transitions_minute)}")
            print(f"lightrise:{light}")
            print("")

        #if is_sunrise:
        #    progress = ((now-start_time_lightset).total_seconds()/(60*duration_transitions_minute))
        #    light = 1023 - progress*1023

        #    print(f"start sunrise: {start_time_sunrise}")
        #    print(f"sunrise: {is_sunrise}, light going off")
        #    print(f"progress sunrise: {progress}")
        #    print(f"sunrise:{light}")
        #    print("")

        print(f"start sunset:{start_time_sunset}")
        print(f"sunset: {is_sunset}, light coming on")
        if is_sunset:
            light = (now-start_time_sunset).total_seconds()/(60*duration_transitions_minute)*1023

            print(f"progress sunset: {(now-start_time_sunset).total_seconds()/(60*duration_transitions_minute)}")
            print(f"sunset: {is_sunset}")
            print("")

    else:
        print("db light on")
        light = light_db

    print(f"start lightset:{start_time_lightset}")
    print(f"lightset: {is_lightset}, light going off")
    if is_lightset:
        light = 1023 - ((now-start_time_lightset).total_seconds()/(60*duration_transitions_minute))*1023

        print(f"progress lightset: {(now-start_time_lightset).total_seconds()/(60*duration_transitions_minute)}")
        print(f"lightset: {is_lightset}")

        if not light:
            if not light_db == light:
                insert_to_db("farm_light", 0, db_connection, db_cursor)


    light = min([1023, light])
    light = max([light, 0])

    light_fixed = int(math.pow(light/1023,2)*1023)
    
    print(f"brightness: {light/1023}")
    print(f"calculated pwm: {light_fixed}")

    if alarm_state:
        ok_to_pump_time = start_time_lightrise + datetime.timedelta(minutes = duration_transitions_minute)
    else:
        ok_to_pump_time = now.replace(hour=12, minute=0)

    if (ok_to_pump_time-now).total_seconds() < 0 and alarm_state and not is_lightset:
        watering_duration = get_from_db("watering_duration", db_cursor)
        watering_period = get_from_db("watering_period", db_cursor)
        if not now.hour%watering_period and now.minute == 50 and now.second < watering_duration-1:
            insert_to_db("pump_state", 1023, db_connection, db_cursor)
            print(f"turning pump on for {watering_duration}s")
            t = threading.Thread(target=turn_off, args=(watering_duration,))
            t.start()

    pump_state = get_from_db("pump_state", db_cursor)

    print(f"pump: {pump_state}")

    db_connection.close()

    if light_fixed > 512:
        light_fixed = 1023
    else:
        light_fixed = 0
             
    return f"{int(light_fixed)},{int(pump_state)}"
