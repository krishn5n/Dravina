import json
import os
from google import genai
from google.genai import types
import getkb
from pydantic import BaseModel
from typing import List
from dotenv import load_dotenv
from mem0 import Memory
from mem0.configs.base import MemoryConfig, LlmConfig, EmbedderConfig, VectorStoreConfig
from qdrant_client import QdrantClient
import logging
from typing import Dict,List

from google.genai.types import FunctionCall,FunctionResponse

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Fixed function declaration - corrected ARRAY type
get_mutual_funds_set_declaration = {
    "name": "get_mutual_funds_set",
    "description": "Get specific mutual fund recommendations with detailed information using fund types as tags. This should be called AFTER getting fund types from details_to_types to get actual fund names and details.",
    "parameters": {
        "type": "object",
        "properties": {
            "tags": {
                "type": "array",  # Fixed: was "ARRAY", should be "array"
                "items": {
                    "type": "string"  # Fixed: was "STRING", should be "string"
                },
                "description": "Array of fund types (like 'Large Cap Funds', 'Multi Cap Funds') obtained from details_to_types tool to get specific fund recommendations"
            }
        },
        "required": ["tags"]
    }
}

def get_mutual_funds_set(tags: List[str]) -> List[dict[str, str]]:
    '''
    Get details of mutual funds using tags specified like equity or debt.

    Args:
        tags: List of tags used for accessing mutual funds

    Returns:
        List of dictionaries of data consisting of details
    '''
    try:
        mutual_list = getkb.obtain_mutual_funds(tags)
        return mutual_list
    except Exception as e:
        logger.error(f"Error getting mutual funds: {e}")
        return []

# Fixed function declaration - corrected STRING type and enum values
get_info_about_fund_declaration = {
    "name": "get_info_about_fund",
    "description": "Get details about a specific fund type",
    "parameters": {
        "type": "object",
        "properties": {
            "based_category": {
                "type": "string",  # Fixed: was "STRING", should be "string"
                "enum": ["structure", "asset class", "investment objectives", "portfolio management", "speciality", "risk appetite"],
                "description": "Select the classification category under which to suggest mutual fund types"
            },
            "fund": {
                "type": "string",  # Fixed: was "STRING", should be "string"
                "description": "Type of fund like equity or debt for which details are required"
            }
        },
        "required": ["based_category", "fund"]
    }
}

def get_info_about_fund(based_category: str, fund: str):
    ''' 
    Get details about a specific fund type and a classification category.

    Args:
        based_category: Select the classification category under which to suggest mutual fund types
        fund: Type of fund like equity or debt for which details are required
        
    Returns:
        Dictionary with fund information
    '''
    try:
        fund_info = getkb.obtain_fund_type_info(based_category, fund)
        return fund_info
    except Exception as e:
        logger.error(f"Error getting fund info: {e}")
        return {"result": "Error retrieving fund information"}

# Fixed function declaration - corrected STRING type
details_to_types_declaration = {
    "name": "details_to_types",
    "description": "Get fund types based on risk and duration preferences. This should be called FIRST to determine suitable fund types, then use get_mutual_funds_set with these types as tags.",
    "parameters": {
        "type": "object",
        "properties": {
            "risk": {
                "type": "string",  # Fixed: was "STRING", should be "string"
                "enum": ["high risk", "medium risk", "low risk", "all risk"],
                "description": "Risk level preference: high, medium, low or all risks. Provide as 'all risk' if unspecified."
            },
            "time": {
                "type": "string",  # Fixed: was "STRING", should be "string"
                "enum": ["short term", "medium term", "long term", "all term"],
                "description": "Duration best suited where less than 3 years implies short term, 3-5 implies medium and 5+ years for long term. Provide as 'all term' if unspecified."
            },
        },
        "required": ["risk", "time"]
    }
}

def details_to_types(risk: str, time: str):
    risk = risk.lower()
    time = time.lower()

    risk_data = {
        'high risk': {
            'short term': ['Credit Risk Fund', 'Hybrid Fund'],
            'medium term': ['Multi Cap Funds'],
            'long term': ['Mid Cap Funds', 'Small Cap Funds']
        },
        'medium risk': {
            'short term': ['Low duration funds', 'Ultra short duration funds'],
            'medium term': ['Balanced Advantage funds'],
            'long term': ['Multi Cap Funds'],
        },
        'low risk': {
            'short term': ['Overnight funds', 'Liquid Funds'],
            'medium term': ['Short duration funds', 'Gilt Funds'],
            'long term': ['Large Cap Funds']
        }
    }

    try:
        if risk == 'all risk' and time == 'all term':
            return risk_data
        elif risk == 'all risk':
            final_value = {'high risk': [], 'medium risk': [], 'low risk': []}
            for i in risk_data:
                if time in risk_data[i]:
                    final_value[i] = risk_data[i][time]
                else:
                    final_value[i] = []
            return final_value
        elif time == 'all term':  # Fixed: was 'all time', should be 'all term'
            return risk_data.get(risk, {})
        else:
            return risk_data.get(risk, {}).get(time, [])
    except Exception as e:
        logger.error(f"Error in details_to_types: {e}")
        return []
    
class Userbehav(BaseModel):
    risk_tolerance:str
    time_horizon:str

def analyze_user_profile(query):
    system_prompt = f'''
    You are a professional psychologist who analyzes human emotions to provide insights on an individuals risk mindset and also analyse the duration of funds.

    #Guidelines
    - Risk can be either 'conservative', 'moderate' or 'aggressive' or if none match 'ready for anything'
      - Example: "high growth needed" - aggressive 
      - Example: "steady growth needed" - moderate
      - Example: "not sure about risk" - conservative
      - Example: "worried about losing" - conservative
      - Example: "as soon as possible" - aggressive
    - Time can be either 'long term' , 'medium term' or 'short term' or if none match 'ready for anything'
      - Example: "till retirement" - long term
      - Example: "for the next 10 years" - long term
      - Example: "immediate" - short term
    '''
    client = genai.Client()
    config = types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(
            thinking_budget=-1  # Dynamic thinking
        ),
        response_mime_type="application/json",
        response_schema=Userbehav
    )
    
    contents = [
        types.Content(
            role="user", parts=[types.Part(text=f"{system_prompt}")]
        ),
        types.Content(
            role="user", parts=[types.Part(text=f"{query}")]
        )
    ]
    response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=contents,
    config=config
    )

    retval:Userbehav = response.parsed
    return retval

class AdviceGiven(BaseModel):
    finance_advice: List[Dict[str,str]]

def key_finance_advice(advice):
    system_prompt = f'''
    You are a professional financial advisor who analyzes financial advice to return the details of the advice.

    #Example of finance advice
    Advice: 

    '''
    client = genai.Client()
    config = types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(
            thinking_budget=-1  # Dynamic thinking
        ),
        response_mime_type="application/json",
        response_schema=Userbehav
    )
    
    contents = [
        types.Content(
            role="user", parts=[types.Part(text=f"{system_prompt}")]
        ),
        types.Content(
            role="user", parts=[types.Part(text=f"{query}")]
        )
    ]
    response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=contents,
    config=config
    )

def call_tool(name, args):
    """Enhanced tool calling with error handling"""
    try:
        if name == "get_mutual_funds_set":
            return get_mutual_funds_set(**args)
        elif name == "get_info_about_fund":
            return get_info_about_fund(**args)
        elif name == "details_to_types":
            return details_to_types(**args)
        else:
            return {"error": f"Unknown tool: {name}"}
    except Exception as e:
        logger.error(f"Error calling tool {name}: {e}")
        return {"error": f"Error executing {name}: {str(e)}"}

'''
Memory -> 
    Get memory
    Add Memory
'''

def memory(task,userid,messages=None):
    try:
        gemini_api_key = os.getenv("GOOGLE_API_KEY")
        llm_config_data = {
            'api_key': gemini_api_key,
            'model': 'gemini-2.5-flash'
        }

        embed_config_data = {
            'api_key': gemini_api_key,
            'model': 'models/text-embedding-004'
        }

        qdrant_specific_config_data = {
            "collection_name": "Dravina",
            "url": os.getenv('QDRANT_URL'),
            "api_key": os.getenv('QDRANT_API_KEY'),
            "on_disk": True,
            "embedding_model_dims":768,
        }

        configs = MemoryConfig(
            llm=LlmConfig(
                provider='gemini',
                config=llm_config_data
            ),
            embedder=EmbedderConfig(
                provider='gemini',
                config=embed_config_data
            ),
            vector_store=VectorStoreConfig(
                provider='qdrant',
                config=qdrant_specific_config_data
            )
        )
        client = Memory(config=configs)

        if task == "get_memory":
            return client.get_all(user_id = str(userid), limit = 20)
        elif task == "add_memory":
            tosend,tonotsend = part_to_memory(messages)
            client.add(messages=tosend, user_id=str(userid))
            # client.add(messages=tonotsend, user_id=str(userid),infer=False)
        elif task == "add_memory_option":
            client.add(messages=messages, user_id=str(userid),infer=False)
        return {}
    except Exception as e:
        logger.error(f"Error in memory: {e}")
        return {}

def part_to_memory(messages):
    tosend = [[],[]]
    for content in messages:
        parts = content.parts
        if content.role == "model":
            part = content.parts[0]
            if part and part.text:
                continue
        if parts:
            for part in parts:
                if part.text:
                    vals = {}
                    vals['content'] = part.text
                    vals['role'] = content.role
                    if part.text.startswith("Result -"):
                        
                        tosend[1].append(vals)
                    else:
                        tosend[0].append(vals)
                elif part.function_call:
                    vals = {}
                    vals['content'] = part.function_call
                    vals['role'] = content.role
                    tosend.append(vals)
                elif part.function_response:
                    vals = {}
                    vals['content'] = part.function_response
                    vals['role'] = content.role
                    tosend.append(vals)
    return tosend


def get_finance_advice(query,userid):
    user_profile = analyze_user_profile(query)
    
    system_prompt = f'''
    You are a professional financial advisor who provides personalized investment insights using reasoning and available tools.

    # USER PROFILE ANALYSIS
    Based on the user's input, here's their profile:
    - Risk Tolerance: {user_profile.risk_tolerance}
    - Time Horizon: {user_profile.time_horizon}
    

    # MANDATORY TOOL USAGE WORKFLOW
    You MUST follow this exact sequence:
    
    1. **STEP 1 - Analyze User Profile**: Carefully analyze the user's:
       - Age, income, expenses, and savings capacity
       - Investment timeline and goals
       - Risk tolerance and Time Horizon as mentioned
       - Financial behavior patterns and emotional indicators
    
    2. **STEP 2 - Get Fund Types**: Call `details_to_types` based on user's risk appetite and investment timeline
    
    3. **STEP 3 - Get Specific Funds (MANDATORY)**: Call `get_mutual_funds_set` with fund types as tags
       - CRITICAL: Remove the word "fund" from tags when calling this tool
       - Example: "Large Cap Funds" → use tag "large cap"
       - Example: "Multi Cap Funds" → use tag "multi cap"  
       - Example: "Equity Funds" → use tag "equity"
       - Example: "Debt Funds" → use tag "debt"
    
    4. **STEP 4 - Make Strategic Recommendations**: 
       - **DO NOT list all available funds**
       - **SELECT 2-4 specific funds maximum** based on user's profile
       - **ALLOCATE percentage of monthly savings** to each selected fund
       - **JUSTIFY each selection** with reasoning based on user's situation
       - Use the following prioritization for each mutual fund:

            1. Prefer **higher 'return'** values. This is the most important metric (highest weight).
            2. Among funds with similar returns, prefer funds with **lower 'expense ratio'** (cost matters more in the long run).
            3. If both return and expense ratio are similar, prefer funds with **higher 'aum'** (indicates popularity and stability).
            4. Avoid funds with significant **'decrease from last time'** as a flag for decrease of funds using the return.
            5. If needed to break ties further, use the **'tags'** field:
            - Prefer thematic tags if looking for sectoral/thematic bets.

            Do not rely on **'current value'** for comparison; it reflects unit NAV, which is not an indicator of performance.
    
    5. **STEP 5 - Optional Details**: Call `get_info_about_fund` using the category and fund type for additional context if needed

    # CRITICAL ADVISORY RULES
    - **NEVER provide final results without calling get_mutual_funds_set**
    - **ALWAYS convert fund types to proper tags by removing "fund" and "funds"**
    - **SELECT specific funds, don't list all options**
    - **ALLOCATE percentages based on user's risk profile and timeline**
    - **JUSTIFY selections with personalized reasoning**
    - **Consider emotional indicators in user's language**
    - **Start final results with "Result - " in markdown format**

    # USER ANALYSIS FRAMEWORK
    When analyzing users, consider:
    - **Risk Tolerance Indicators**: 
      - "I don't know if I'm ready to take risk" = Conservative approach
      - "I want aggressive growth" = High risk tolerance
      - "I'm worried about losing money" = Very conservative
    - **Time Horizon Impact**:
      - Long-term goals (10+ years) = More equity allocation
      - Medium-term goals (3-10 years) = Balanced approach
      - Short-term goals (<3 years) = More debt/liquid funds
    - **Age-based Allocation Rule**: 
      - Equity allocation = 100 - age (as starting point)
      - Adjust based on risk tolerance and goals

    # PERSONALIZED RECOMMENDATION FORMAT
    Your final recommendations should include:
    1. **Portfolio Allocation Strategy** (e.g., 60% equity, 40% debt)
    2. **2-4 Selected Funds** with specific allocation percentages
    3. **Monthly Investment Amount** for each fund
    4. **Reasoning** for each selection based on user's profile
    5. **Review Timeline** (when to reassess)

    # Tax Information to Include
    - Investment money are taxable
    - For equity funds, Long Term Capital Gains (12+ months) are taxed at 10% above Rs 1 Lakh exemption
    - Short Term Capital Gains (<12 months) are taxed at 15%
    - For debt funds, indexation benefit is available for capital gains

    # Investment Focus Areas
    - Mutual funds (equity/debt mix based on age and risk profile)
    - Gold and silver as hedge against inflation (when relevant)
    '''

    try:
        client = genai.Client()
        tools = types.Tool(function_declarations=[
            get_mutual_funds_set_declaration,
            get_info_about_fund_declaration,
            details_to_types_declaration
        ])
        config = types.GenerateContentConfig(
            tools=[tools],
            thinking_config=types.ThinkingConfig(
                thinking_budget=-1  # Dynamic thinking
            )
        )
        
        memory_list = memory("get_memory",userid)
        logger.info(f"Memory list: {memory_list}")
        contents = [
            types.Content(
                role="model", parts=[types.Part(text=f"{system_prompt}")]
            ),
            types.Content(
                role="user", parts=[types.Part(text=f"{query}")]
            )
        ]
        if memory_list:
            results = memory_list.get("results")
            for i in results:
                contents.append(types.Content(
                    role="user", parts=[types.Part(text=i['memory'])]
                ))

        loop = 1
        max_loops = 10
        
        while loop < max_loops:
            try:
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=contents,
                    config=config
                )

                logger.info(f"Response: {response}")
                candidate = response.candidates[0]
                parts = candidate.content.parts
                logger.info(f"Parts: {parts}")

                # Check if we have a final result
                for part in parts:
                    if part.text and part.text.startswith("Result -"):
                        contents.append(types.Content(
                            role="user",
                            parts=[types.Part(text=part.text)]
                        ))
                        memory("add_memory",userid,contents)
                        return part.text
                    
                    if part.function_call:
                        name = part.function_call.name
                        args = dict(part.function_call.args)  # Convert to dict
                        logger.info(f"Calling tool: {name} with args: {args}")
                        result = call_tool(name, args)
                        logger.info(f"Tool result obtained",len(result))
                        contents.append(types.Content(
                            role="user",
                            parts=[types.Part(function_call=FunctionCall(name=name,args=args,id=part.function_call.id))]
                        ))
                        dict_response = {
                            "output": result
                        }
                        contents.append(types.Content(
                            role="user",
                            parts=[types.Part(function_response=FunctionResponse(response=dict_response,will_continue=False,name=name,id=part.function_call.id))]
                        ))
                    else:
                        contents.append(types.Content(role="model", parts=[part]))
                        print(contents[-1])
                        if part.text:
                            print(f"Model response: {part.text[:200]}...")
                
                loop += 1
                
            except Exception as e:
                logger.error(f"Error in generation loop {loop}: {e}")
                return f"Error: {str(e)}"
        
        return "Maximum iterations reached without final result"
        
    except Exception as e:
        logger.error(f"Error in get_finance_advice: {e}")
        return f"Error initializing finance advisor: {str(e)}"


if __name__ == "__main__":
    try:
        result = get_finance_advice(
            "I earn close to 40000 and i spend 10000 on fixed expenses, 1000 on variable and 15000 on casual expenses. I am of age 33 and i want to save money such that by to live happily and have savings by 50. I dont know if i am ready to take risk",100
        )
        # memlist = memory("get_memory",100)
        # vals = json.dumps(memlist,indent=4)
        print(result)        
    except Exception as e:
        logger.error(f"Error running finance advisor: {e}")