import json
import requests
import os
from openai import OpenAI
from pydantic import BaseModel, Field
import getkb
from typing import List

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

#tool 1 -> Given input of tags to search for
#Output -> Return the list of mutual funds that i can return
def get_mutual_funds_set(tags:List[str],risk:str):
    retval = []
    to_search = set(tags)
    mutual_list = getkb.obtain_mutual_funds()
    for i in mutual_list:
        vals = set(i['tags'])
        vals.intersection(tags)
        if vals:
            retval.append(i)
    return retval

#tool 2 -> Obtain the necessary information about a fund
#input -> Fund name you want input for
#output -> String of description about fund
def get_info_about_fund(fund:str):
    fund_info = getkb.obtain_fund_info()
    if fund in fund_info:
        return fund_info[fund]
    else:
        return "No available information for this fund, Proceed with another fund with similar characteristics"
    
#tool 3 -> Obtain past 6 years of data on gold and silver rates
#input -> None -> gold or silver or both -> int -> 0 na gold, 1 na silver, 2 na both
#output -> Json of values
def get_history_stone(option:int):
    stone_data = getkb.obtain_stone_vals()
    if option==2:
        return stone_data
    elif option==1:
        return stone_data['silver']
    else:
        return stone_data['gold']

def get_finance_advice():
    system_prompt = '''
    You are a helpful finance assistant that provides personalized investment insights using reasoning and available tools.

    #Available tools
    - List of Mutual Funds available based on need specified. 

    # Necessary Questions to Ask
    - What risk are you willing to take , Compulsory - High , Medium or Low
    - What time period , Compulsory - Short term (up to 3 years), Medium term (3-5 years), Long term (5 years and above)
    - What kind of Liquidity , Not Compulsory- Where you want to raise money for a short period
    - What expense ratio will you , Not Compulsory - 

    #Informations to convey
    - Investment money are taxable
    - For equity funds, Long Term Capital Gains (holding period of 12 months and above) are taxed at 10 percent over and above the exemption limit of Rs 1 Lakh.
    - Short Term Capital Gains (holding period of less than 12 months) are taxed at 15%.
    - For Debt funds, an indexation benefit is available for capital gains realized.
    
    # Guidelines
    - Always consider user's age, income, current spending, and risk tolerance
    - Provide specific, actionable advice with reasoning
    - Be clear and concise in your final recommendations

    # Investment Options to Consider
    Research these options based on user's profile:
    - Mutual funds (equity/debt mix based on age)
    - Gold and silver based on past 6 years of data (as hedge against inflation)

    # Expert Suggestion
    - Short Term and High Risk - Credit Risk Fund, Hybrid Fund
    '''
    messages = [
        {"role": "system", "content": system_prompt},
    ]

    
    # Get the possible list of mutual funds based on the category
    def get_specific_mutual_funds(category):
        possible_list = []
        return json.dumps(possible_list)


    response = client.responses.create(
        model="gpt-4.1",
        instructions="Talk Semi Professional and empathetic.",
    )

