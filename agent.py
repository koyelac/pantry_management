import json
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta, date
import send_msg as msgapp
import schedule
import time
import os
from dotenv import load_dotenv

# This is the non-LLM agent that manages stored inventory data
# This contains the scheduled function that runs on a specific hour
# This agent also has routine that makes API call to fetch weather data
# and finds the average max temperature for the next 48 hrs
# If that exceeds a certain threshold, the expiry date is adjusted for
# counter items only. It is assumed refridgerated ones will not be affected by
# high temperature
# schedule library is used to make it os agnostic

load_dotenv()
base_url = 'https://api.openweathermap.org/data/2.5/forecast?lat=22.5744&lon=88.3629&appid='
api = os.getenv("WEATHER_API_KEY")
api_url = base_url+api
csv_file = "sample_inventory.csv"
threshold_temp = 20
EXECUTION_TIME = "11:00" # set to run at 11 am system time

def fetch_weather():
    """ fetches weather data and sends the data as python dictionary """
    try:
        
        response = requests.get(api_url)
        if response.status_code == 200:
            pydict = json.loads(response.text)
        else:
            return {"success":False, "error":response.status_code}
        return {"success":True, "w_data":pydict}
    except Exception as e:
        return {"success":False, "error" : e}

def get_avg(pydict):
    """ gets the avg max temp"""
    #pydict = fetch_weather()
    max_temp_list = [
        item["main"]["temp_max"] - 273.15
        for item in pydict["list"]
        ][:16]
    avg_max_temp = sum(max_temp_list)/len(max_temp_list)
    return avg_max_temp

def update_expiry():
    """ decreases the expiry date by one day. Called when a certain condition
        is met """
    try:
        
        df = pd.read_csv(csv_file)
        df["expiry_dt"] = pd.to_datetime(df["expiry_dt"], format = "%d-%m-%Y")
        condition = (df["storage"]=="counter")
        df.loc[condition, "expiry_dt"] = df.loc[condition, "expiry_dt"] - timedelta(days=1)
        df["expiry_dt"] = df["expiry_dt"].dt.strftime("%d-%m-%Y")
        df.to_csv(csv_file, index=False)
        return {"success":True, "msg": "Expiry dates updated"}
    except Exception as e:
        return {"success":False, "error":e}
def check_stocks():
    """ gets the list of items expiring by next 2 days"""
    try:
        df = pd.read_csv(csv_file)
        df["expiry_dt_dt"] = pd.to_datetime(df["expiry_dt"], format="%d-%m-%Y")
        curr_date = datetime.today()
        condition = ((df["expiry_dt_dt"]-curr_date).dt.days < 3)
        if condition.any():
            
            df.loc[condition, "status"] = "flagged"
            df.drop(columns = ["expiry_dt_dt"], inplace=True)
            df.to_csv(csv_file, index=False)
            check_food_list = df.loc[condition, "name"].tolist()
            check_food = ",".join(check_food_list)
            return {"success":True, "inventory_update":True, "check_list":check_food}
        else:
            return {"success":True, "inventory_update":False}
    except Exception as e:
        return {"success":False, "error":e}
    
        

def check_spoilage():
    """ calls appropriate sub routines to analyze stock info based on weather"""
    get_weather = fetch_weather()
    if get_weather["success"]:
        avg_temp = get_avg(get_weather["w_data"])
        if avg_temp>threshold_temp:
            inv_update = update_expiry()
            stock_check = check_stocks()
            if stock_check["success"] and stock_check["inventory_update"]:
                #alert_user(stock_check["check_list"], condition=True)
                return {"success":True, "inventory_update":True, "msg": "Inventory updated"}
            else:
                return {"success":True, "inventory_update":False, "msg": "No Inventory update needed"}
            
        else:
            return {"success":True, "inventory_update":False, "msg": "No Inventory update needed"}
        
    else:
        return get_weather

def routine_msg():
    """ finds the items flagged and calls function to send user whatsapp msg"""
    try:
        df = pd.read_csv(csv_file)
        condition = (df["status"] == "flagged")
        mylist = df.loc[condition, "name"].tolist()
        check_food_list = ",".join(mylist)
        alert_user(check_food_list)
        return {"success":True, "msg": "Inventory refreshed successfully"}
    except Exception as e:
        print(f"Cannot be alerted for condition {e}")
        return {"success":False, "error": e}
               
    

def alert_user(checklist, condition=False):
    """ whatsapp message sending """
    if condition:
        msg = f"Attention from your Pantry! Due to upcoming bad weather, {checklist} are getting spoiled"
    else:
        msg = f"Attention from your Pantry! {checklist} are getting spoiled by next 2 days"
        
        
    msgapp.send_message(msg)

def routine_agent():
    try:

        cond = check_spoilage()
        if cond["success"]:
            cond2 = routine_msg()
            return cond2
        else: 
            return cond
    except Exception as e:
        return {"success": False, "error": e}
            

    

def run_scheduler():
    """
    This loop continuously checks if a scheduled job is due to run.
    """
    while True:
        try:
            # Check for any pending jobs
            schedule.run_pending()
        except Exception as e:
            # Simple error handling for robustness
            print(f"An error occurred in the scheduler loop: {e}")
            
        # The scheduler checks every 60 seconds (adjust as needed, 1 second is fine)
        time.sleep(1)
schedule.every().day.at(EXECUTION_TIME).do(routine_agent) 
print(f"Scheduler initialized. Routine is set to run daily at {EXECUTION_TIME} (local time).")


if __name__ == "__main__":

    run_scheduler()
    #routine_agent()
        
    
    
    
    
        
