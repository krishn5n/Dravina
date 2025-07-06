import json
import requests
import os
from google import genai
from google.genai import types
import getkb
from typing import List
from dotenv import load_dotenv

load_dotenv()


get_mutual_funds_set_declaration = {
    "name": "get_mutual_funds_set",
    "description": "Get details of mutual funds using tags specified like equity or debt.",
    "parameters": {
        "type": "object",
        "properties": {
            "tags": {
                "type": "ARRAY",
                "items":{
                    "type":"STRING"
                },
                "description":"The array of tags of mutual funds that want to be accessed"
            }
        },
        "required": ["tags"]
    }
}

def get_mutual_funds_set(tags:List[str]) -> List[dict[str,str]]:
    '''
        Get details of mutual funds using tags specified like equity or debt.

        Args:
            tags: List of tags used for accessing mutual funds

        Returns:
            List of dictionaries of data consisting of details
    
    '''
    mutual_list = getkb.obtain_mutual_funds(tags)
    return mutual_list



get_info_about_fund_declaration = {
    "name": "get_info_about_fund",
    "description": "Get details about a specific fund type ",
    "parameters": {
        "type": "object",
        "properties": {
            "based_category":{"type": "STRING","enum":["structure","asset class", "investment objectives", "portfolio management", "speciality" , "risk appetite"],"description":"Select the classification category under which to suggest mutual fund types"},
            "fund": {"type": "STRING","description":"Type of fund like equity or debt for which details are required"}
        },
        "required": ["based_category","fund"]
    }
}

#tool 3 -> Obtain past 6 years of data on gold and silver rates
#input -> None -> gold or silver or both -> int -> 0 na gold, 1 na silver, 2 na both
#output -> Json of values
def get_info_about_fund(based_category:str,fund:str):
    ''' 
        Get details about a specific fund type and a classification category.

        Args:
            based_category: Select the classification category under which to suggest mutual fund types
            fund: Type of fund like equity or debt for which details are required
            
        Returns:
            List of dictionaries of data of data and cost as keys
    '''
    fund_info = getkb.obtain_fund_type_info(based_category,fund)
    return fund_info

# get_history_stone_declaration = {
#     "name": "get_history_stone",
#     "description": "Get historical cost price of gold for 24 Karat per 10 gram and silver per kilogram",
#     "parameters": {
#         "type": "object",
#         "properties": {
#             "option": {"type": "STRING","enum":["0","1","2"],"description":"Specify '0' for gold, '1' for silver and '2' for both"}
#         },
#         "required": ["option"],
#     }
# }
# def get_history_stone(option:str):
#     stone_data = getkb.obtain_stone_vals(option)
#     return stone_data

#tool 4 -> Give mutual fund list based on what risk and time to be given
#input -> Risk and time based on needs
#output -> JSON data of fund types based on risk or time
details_to_types_declaration = {
    "name": "details_to_types",
    "description": "Get types of mutual funds based on risk or duration",
    "parameters": {
        "type": "object",
        "properties": {
            "risk": {
                "type": "STRING",
                "enum":["high risk","medium risk","low risk","all risk"],
                "description": "Risk level preference: high, medium, low or all risks. Provide as 'all risk' if unspecified."
                },
            "time": {
                "type": "STRING",
                "enum":["short term","medium term","long term","all term"],
                "description": "Duration best suited where less than 3 years implies short term, 3-5 implies medium and 5+ years for long term. Prove as 'all term' if unspecified."
                },
        },
        "required" : ["risk","time"]
    }
}
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


    if risk=='all risk' and time == 'all term':
        return risk_data
    elif risk=='all risk':
        final_value = {'high risk':[],'medium risk':[],'low risk':[]}
        for i in risk_data:
            final_value[i] = risk_data[i][time]
        return final_value
    elif time=='all time':
        return risk_data[risk]
    else:
        return risk_data[risk][time]

def call_tool(name,args):
    if name=="get_mutual_funds_set":
        return get_mutual_funds_set(**args)
    elif name=="get_info_about_fund":
        return get_info_about_fund(**args)
    # elif name=="get_history_stone":
    #     return get_history_stone(**args)
    elif name=="details_to_types":
        return details_to_types(**args)

def get_finance_advice(query):
    system_prompt = '''
    You are a helpful finance assistant that provides personalized investment insights using reasoning and available tools.

    #Informations to convey
    - Investment money are taxable
    - For equity funds, Long Term Capital Gains (holding period of 12 months and above) are taxed at 10 percent over and above the exemption limit of Rs 1 Lakh.
    - Short Term Capital Gains (holding period of less than 12 months) are taxed at 15%.
    - For Debt funds, an indexation benefit is available for capital gains realized.

    # Guidelines
    - Always use the tools available to fetch mutual fund details and convert user data into structured finance types.
    - When deciding mutual funds, **invoke tools** instead of making assumptions.
    - Respond with a function call using one of the tools if more information is needed or if fetching fund details.
    - Provide specific, actionable advice with reasoning
    - When informing your final results, start the result with "Result - " following a markdown format

    # Investment Options to Consider
    Research these options based on user's profile:
    - Mutual funds (equity/debt mix based on age)
    - Gold and silver based on past 6 years of data (as hedge against inflation)

    '''

    client = genai.Client()
    tools = types.Tool(function_declarations=[get_mutual_funds_set_declaration,get_info_about_fund_declaration,details_to_types_declaration])
    config = types.GenerateContentConfig(
        tools=[tools],
        thinking_config=types.ThinkingConfig(
            thinking_budget=-1               # Dynamic thinking (or set a fixed token budget like 1024)
        )
    )
    contents = [
        types.Content(
            role="user",parts=[types.Part(text=f"{system_prompt}")]
            ),
        types.Content(
            role="user", parts=[types.Part(text=f"{query}")]
        )
]


    loop = 1
    while True and loop<10:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
            config=config
        )

        candidate = response.candidates[0]
        parts = candidate.content.parts
        usage = response.usage_metadata
        # print(f"Thinking tokens: {usage.thoughts_token_count}, Output tokens: {usage.candidates_token_count} for loop {loop}")

        for part in parts:
            if part.text and part.text.startswith("Result -"):
                # print("I got result")
                return part.text
            if part.function_call:
                name = part.function_call.name
                args = part.function_call.args

                result = call_tool(name, args)
                function_response_text = json.dumps({
                    "tool_used": name,
                    "response": result
                })
                contents.append(types.Content(
                    role="user",
                    parts=[types.Part(text=function_response_text)]
                ))

            else:
                contents.append(types.Content(role="model", parts=[part]))
        loop += 1
print(get_finance_advice("I earn close to 40000 and i spend 10000 on fixed expenses, 1000 on variable and 15000 on casual expenses. I am of age 33 and i want to save money such that by to live happily and have savings by 50. I dont know if i am ready to take risk "))

