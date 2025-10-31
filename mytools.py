import pandas as pd
import numpy as np
import os
import math
import json
from datetime import datetime, timedelta, date
import csv
from typing import Dict
from dateutil.relativedelta import relativedelta

# the user specific tools the image agent needs

csv_file = "sample_inventory.csv"

def fresh_stocks_format(json_data :Dict):
    """
        checks the items identified by OCR, looks for expiry date in raw_food_db
        file and calculates the expiry dates for non packaged stuff.
        Will provide a default expiry date if item not found in the above csv
        Also populates the sample_inventory.csv with new data
    """
    try:
        item_list = json_data["items"]
        nu_stock = pd.DataFrame(columns=["name", "expiry_dt", "status","storage"])
        for item in item_list:
            if item["type"] == "grocery":
                print("Grocery found")
                match_items = pd.read_csv("raw_food_db.csv")
                name_list = list(match_items["name"])
                print("Opened sample db csv")
                current_date = datetime.today()
                if item["name"] in name_list:
                    df_row = match_items[match_items["name"]==item["name"]]
                    days_to_add = int(df_row["shelf_life"])
                    exp = current_date + timedelta(days = days_to_add)
                    storage = df_row["storage"].item()
                    print(f"Storage of {item['name']} is {storage}")
                else:
                    # Add two days as expiry by default if item not found in database
                    print(f"Item not found, adding default day 2 and counter storage for grocery {item['name']}")
                    exp = current_date + timedelta(days = 2)
                    storage = "counter"
                nu_stock.loc[len(nu_stock)] = [item["name"], pd.to_datetime(exp).strftime("%d-%m-%Y"), "open", storage]
                print("New grocery item added while preparing sheet")
                
            else:
                print("Packaged item found")
                if item["expiry_date"]:
                    exp = pd.to_datetime(item["expiry_date"], format='%d-%m-%Y')
                elif item["mfg_date"] and not item["expiry_date"]:
                    if item["time_denom"] == "d":
                        exp = pd.to_datetime(item["mfg_date"], format = '%d-%m-%Y') + timedelta(days = int(item["time_remaining"]))
                         
                    else:
                        exp = exp = pd.to_datetime(item["mfg_date"], format = '%d-%m-%Y') + relativedelta(months = int(item["time_remaining"]))
                else:
                    pass
                nu_stock.loc[len(nu_stock)] = [item["name"], pd.to_datetime(exp).strftime("%d-%m-%Y"), "open", "fridge"]
                print("New packaged item added while preparing sheet")
        return {"success": True, "data" : nu_stock}
    except Exception as e:
        return {"success": False, "error" : e}


def clear_old_optimized(df):
    print("Clearing old items (Optimized)")
    if "Unnamed: 0.1" in df.columns:
        df.drop("Unnamed: 0", axis=1, inplace=True)
    # Convert 'expiry_dt' to datetime objects for comparison
    df['expiry_dt_dt'] = pd.to_datetime(df['expiry_dt'], format='%d-%m-%Y')
    curr_date = datetime.today()

    # Define the condition for ROWS TO KEEP:
    # KEEP if status is NOT 'flagged'
    condition_keep_1 = (df['status'] != 'flagged')
    
    # OR KEEP if status IS 'flagged' AND the expiry date is NOT in the past
    condition_keep_2 = (df['status'] == 'flagged') & (df['expiry_dt_dt'] >= curr_date)

    # Combine the conditions using '|' (OR)
    rows_to_keep = condition_keep_1 | condition_keep_2

    # Return a new DataFrame containing only the rows to keep
    # The original DataFrame is NOT modified (inplace=False by default)
    df_cleaned = df[rows_to_keep].drop(columns=['expiry_dt_dt'])

    print(f"Original shape: {df.shape}, Cleaned shape: {df_cleaned.shape}")
    print(df_cleaned.head())
    return df_cleaned


def update_stock(json_data:Dict):
    print("Request recieved to update stock")
    try:
        stock_df = pd.read_csv("sample_inventory.csv")
        print("Finished fetching existing inventory")
        #stock_df = clear_old(stock_df)
        stock_df = clear_old_optimized(stock_df)
        print("Now let us get the new stock info")
        get_data = fresh_stocks_format(json_data)
        if get_data["success"]:
            print('Got the new stock data formatted')
            print(get_data["data"].head())
            nu_stock = get_data["data"]
        else:
            print('Stock data formatting unsuccessful')
            return {"success": False, "error": get_data["error"]}
        updated_stock = pd.concat([stock_df, nu_stock], ignore_index=True)
        if "Unnamed: 0.1" in updated_stock.columns:
            print("Deleting unwanted column")
            updated_stock.drop("Unnamed: 0.1", axis=1, inplace=True)
        print('Concatenating the new stock with remaining')
        updated_stock.to_csv("sample_inventory.csv", index=False)
        print('Writing the new stock successful')
        return {"success" : True, "msg": "New Stock Updated"}
    except Exception as e:
        return {"success": False, "error" : e}
# this tool is used by Agent 3, the donation agent that needs item types for
#searching appropriate organizations for donating those
def fetch_list():
    try:
        df = pd.read_csv(csv_file)
        condition = (df["status"] == "flagged")
        mylist = df.loc[condition, "name"].tolist()
        check_food_list = ",".join(mylist)
        return {"success":True, "checklist":check_food_list}
    except Exception as e:
        return {"success":False, "error":e}
    
if __name__ == "__main__":
    print("Main module here")
    bajar = {"success": True,
             "items" : [
                 {"name" : "ash gourd","type": "grocery"}, {"name" : "pasta", "type": "packaged", "expiry_date": None, "mfg_date" : "16-06-2025", "time_denom": "d", "time_remaining": 210}]}
    print("Let us start from main")
    status = update_stock(bajar)
    if status["success"]:
        print(status["msg"])
    else:
        print(status["error"])
    
                  
        
       

                  
                     
                
                        
                        
                        
