import scrape_data
from typing import List

#Get details about every mutual fund
def obtain_mutual_funds(tags:List[str]):
    print("Getting MF")
    setsearch = set(tags)
    retval = []
    fund_list = scrape_data.mutual_funds()
    for i in fund_list:
        for j in i['tags']:
            if j in setsearch:
                retval.append(i)
                break
    return retval

#Get information on stones
def obtain_stone_vals(option:int):
    print("getting stone")
    list_val = scrape_data.gold_silver_details()
    if option == '0':
        return list_val['gold']
    elif option=='1':
        return list_val['silver']
    return list_val

#Get information on each fund types -> From an api
def obtain_fund_type_info(category:str,fund:str):
    print("Getting Fund types")
    details = scrape_data.mutual_fund_details()
    if category in details:
        if fund in details[category]:
            return {"result":f"{details[category][fund]}"}
    return {"result":"The requested fund information does not exist. Please either provide the desired fund details explicitly, or allow the assistant to proceed with similar fund recommendations based on available preferences."}
