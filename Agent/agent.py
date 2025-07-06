import json
import requests
import os
from openai import OpenAI
from pydantic import BaseModel, Field
import getkb
from typing import List
from dotenv import load_dotenv

load_dotenv()


#tool 1 -> Given input of tags to search for based on their needs
#Output -> Return the list of mutual funds that i can return
def get_mutual_funds_set(tags:List[str]):
    mutual_list = getkb.obtain_mutual_funds(tags)
    return mutual_list

#tool 2 -> Obtain the necessary information about a fund
#input -> Fund type you want input for
#output -> String of description about fund
def get_info_about_fund(based_category:str,fund:str):
    fund_info = getkb.obtain_fund_type_info(based_category,fund)
    return fund_info
    
#tool 3 -> Obtain past 6 years of data on gold and silver rates
#input -> None -> gold or silver or both -> int -> 0 na gold, 1 na silver, 2 na both
#output -> Json of values
def get_history_stone(option:int):
    stone_data = getkb.obtain_stone_vals(option)
    return stone_data

#tool 4 -> Give mutual fund list based on what risk and time to be given
#input -> Risk and time based on needs
#output -> JSON data of fund types based on risk or time
def details_to_types(risk:str,time:str):
    risk = risk.lower()
    time = time.lower()

    risk_data = {
        'high risk':{
            'short term':['Credit Risk Fund', 'Hybrid Fund'],
            'medium term':['Multi Cap Funds'],
            'long term':['Mid Cap Funds','Small Cap Funds']
            },
        'medium risk':{
            'short term':['Low duration funds','Ultra short duration funds'],
            'medium term':['Balanced Advantage funds'],
            'long term':['Multi Cap Funds'],
            },
        'low risk':{
            'short term':['Overnight funds','Liquid Funds'],
            'medium term':['Short duration funds','Gilt Funds'],
            'long term':['Large Cap Funds']
            }
    }


    if len(risk) == 0 and len(time) == 0:
        return risk_data
    if risk:
        if time:
            return risk_data[risk][time]
        else:
            return risk_data[risk]
    else:
        final_value = {'high risk':[],'medium risk':[],'low risk':[]}
        for i in risk_data:
            final_value[i] = risk_data[i][time]

        return final_value
    
tools = [{
    "type": "function",
    "name": "get_mutual_funds_set",
    "description": "Get all mutual funds of the type specified like equity or debt.",
    "parameters": {
        "type": "object",
        "properties": {
            "tags": {
                "type": "array",
                "items":{
                    "type":"string"
                },
                "description":"The array of tags of mutual funds that want to be accessed"
            }
        },
        "required": ["tags"],
        "additionalProperties": False
    },
    "strict": True
    },
    {
    "type": "function",
    "name": "get_info_about_fund",
    "description": "Get details about a specific fund type ",
    "parameters": {
        "type": "object",
        "properties": {
            "based_category":{"type": "string","enum":["structure","asset class", "investment objectives", "portfolio management", "speciality" , "risk appetite"],"description":"Select the classification category under which to suggest mutual fund types"},
            "fund": {"type": "string","description":"Type of fund like equity or debt for which details are required"}
        },
        "required": ["fund"],
        "additionalProperties": False
    },
    "strict": True
    },
    {
    "type": "function",
    "name": "get_history_stone",
    "description": "Get historical cost price of gold for 24 Karat per 10 gram and silver per kilogram",
    "parameters": {
        "type": "object",
        "properties": {
            "option": {"type": "number","enum":[0,1,2],"description":"Specify 0 for gold, 1 for silver and 2 for both"}
        },
        "required": ["option"],
        "additionalProperties": False
    },
    "strict": True
    },
    {
    "type": "function",
    "name": "details_to_types",
    "description": "Get types of mutual funds based on risk or duration",
    "parameters": {
        "type": "object",
        "properties": {
            "risk": {
                "type": ["string", "null"],
                "enum":["high risk","medium risk","low risk"],
                "description": "Risk level preference: high, medium, or low. Leave null if unspecified."
                },
            "time": {
                "type": ["string", "null"],
                "enum":["short term","medium term","long term"],
                "description": "Duration best suited where less than 3 years implies short term, 3-5 implies medium and 5+ years for long term. Leave null if unspecified."
                },
        },
        "additionalProperties": False
    },
    "strict": True
    }]

def call_tool(name,args):
    if name=="get_mutual_funds_set":
        return get_mutual_funds_set(**args)
    elif name=="get_info_about_fund":
        return get_info_about_fund(**args)
    elif name=="get_history_stone":
        return get_history_stone(**args)
    elif name=="details_to_types":
        return details_to_types(**args)

def get_finance_advice(query):
    system_prompt = '''
    You are a helpful finance assistant that provides personalized investment insights using reasoning and available tools.

    # Necessary Questions to Ask with Compulsory or not
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
    - When informing your final results, start the result with "Result - " following a markdown format

    # Investment Options to Consider
    Research these options based on user's profile:
    - Mutual funds (equity/debt mix based on age)
    - Gold and silver based on past 6 years of data (as hedge against inflation)

    '''
    messages = [
        {"role": "system", "content": system_prompt},
        {"role":"user","content":f"{query}"}
    ]

    # client = OpenAI()
    loop = 1
    while True and loop<10:
        response = client.chat.completions.create(
            model="gpt-4.1",
            messages=messages,
            tools = tools,
            tool_choice="auto",
            temperature=0.7,
        )

        curr_iter = response.choices[0].message
        if hasattr(curr_iter,"tool_calls") and curr_iter.tool_calls:
            for tool_call in response.choices[0].message.tool_calls:
                name = tool_call.function.name
                args = json.loads(tool_call.function.arguments)
                messages.append(response.choices[0].message)

                result = call_tool(name, args)
                messages.append(
                    {"role": "tool", "tool_call_id": tool_call.id, "content": json.dumps(result)}
                )
        else:
            messages.append(curr_iter)
            return curr_iter.content

        loop+=1

get_finance_advice("I earn close to 100000 and i spend 20000 on fixed expenses, 10000 on variable and 50000 on casual expenses. I am of age 23 and i want to save money such that by 30 i should have 10x what i have. I am ready to take risk ")

