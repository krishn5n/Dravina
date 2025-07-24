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
import logging
from dateutil.parser import parse

from google.genai.types import FunctionCall,FunctionResponse

load_dotenv()
logging.basicConfig(level=logging.ERROR)
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
    - ALWAYS have risk as'conservative', 'moderate' or 'aggressive' or if none match 'ready for anything'
    - ALWAYS calculate the expected returns if the user specifies the amount of money they want to save and the amount of money they have
      - 20% of salary usually is placed in mutual funds , If more is placed - moderate
      - ALWAYS Calculate returns expected using  X = P* ((1+r)^n) * (1+r) where X is amount expected, P is monthly invested, n is the duration in months , Calculate approximately for r
        - If r <= 15 then risk is conservative
        - If r >= 15 and r<=22 then risk is moderate
        - If r >= 22 then risk is aggressive
      - Example:
        X = 4000000
        P = 30000
        n = 10
        Solving equation of we get  X = P* (((1+r)^n+1) , (1+r)^61 = 40,00,000/30,000
            - Put r = 15 then we get 1.15^61 = 5041, which is greater than 40,00,000/30,000 hence user is conservative
    - Exammple
        X = 4000000
        P = 6000
        n = 5
        Solving equation of we get  X = P* (((1+r)^n+1) , (1+r)^60 *(1+r) = 4000000/6000
            - Put r = 15 then we get 1.15^31 = 76.14, which is lesser than than 4000000/6000 hence user is not conservative
            - Put r = 22 then we get 1.22^31 = 475 which is lesser than 4000000/6000 hence user is not moderate
            - Since we conclude user is aggressive
    - IF the user risk is still not chosen then use the language of the user to determine risk
      - Example: "high growth needed" - aggressive 
      - Example: "steady growth needed" - moderate
      - Example: "not sure about risk" - conservative
      - Example: "worried about losing" - conservative
      - Example: "I want to save as much as I can" - conservative
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

def key_finance_advice(advice):
    system_prompt = '''
    You are an intelligent financial advisor agent designed to extract structured insights from qualitative financial recommendations. Your goal is to identify and summarize:

    - Portfolio allocation strategy
    - Fund names and types
    - Investment amounts
    - Reasoning behind fund selection

    ### Input Example: Financial Advice

    **Portfolio Allocation Strategy:**
    Given your age and long-term goal, an equity allocation around 60–70% is generally recommended. For your conservative risk appetite, we will focus on well-performing Large Cap Equity Funds.

    **Selected Funds and Allocation:**
    You have a monthly savings capacity of ₹14,000. Here's how we can allocate it:

    1. **Nippon India Large Cap Fund**
    - **Monthly Investment:** ₹8,400 (60% of your monthly savings)
    - **Reasoning:** This fund has demonstrated the highest returns (+21.79% p.a.) among available Large Cap options, coupled with a competitive expense ratio (0.65%). It’s suitable for long-term wealth creation with a conservative mindset.

    2. **ICICI Prudential Large Cap Fund**
    - **Monthly Investment:** ₹5,600 (40% of your monthly savings)
    - **Reasoning:** Slightly lower returns (+19.44% p.a.) than Nippon India, but boasts a higher AUM of ₹72,336 Cr, indicating investor confidence and stability. Helps diversify within the Large Cap segment.

    ### Output Format
    Return the result as a structured JSON object:

    [
    {
        "Nippon India Large Cap Fund": {
        "Monthly Investment": "₹8,400",
        "Reasoning": "This fund has demonstrated the highest returns (+21.79% p.a.) among available Large Cap options, coupled with a competitive expense ratio (0.65%). It’s suitable for long-term wealth creation with a conservative mindset."
        },
        "ICICI Prudential Large Cap Fund": {
        "Monthly Investment": "₹5,600",
        "Reasoning": "Slightly lower returns (+19.44% p.a.) than Nippon India, but boasts a higher AUM of ₹72,336 Cr, indicating investor confidence and stability. Helps diversify within the Large Cap segment."
        }
    }
    ]
    
    ### Guidelines
    - You must return the finance advice in the same format as the example.
    - You must summarise the Reasoning in 1-2 lines.
    - You must return the finance advice in the same language as the input.
    '''
    client = genai.Client()
    config = types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(
            thinking_budget=-1  # Dynamic thinking
        ),
        response_mime_type="application/json",
    )
    
    
    contents = [
        types.Content(
            role="user", parts=[types.Part(text=f"{system_prompt}")]
        ),
        types.Content(
            role="user", parts=[types.Part(text=f"{advice}")]
        )
    ]
    
    response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=contents,
    config=config
    )

    candidate = response.candidates[0]
    if candidate and candidate.content and candidate.content.parts:
        parts = candidate.content.parts[0]
        if parts.text:
            return parts.text

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

def datesort(memory):
    print(f"Memory: {memory}")
    created = parse(memory.get("created_at"))
    if getattr(memory, "updated_at", None):
        updated = parse(memory.get("updated_at"))
        created = max(created, updated)
    return created


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
            retval = []
            res = client.get_all(user_id=str(userid),limit=10)
            res = res.get("results",[])
            for i in res:
                if not i['metadata'] or i['metadata']["type"] != "finance_advice" and i["memory"]:
                    retval.append(i)
            print(f"Retval: {retval}")
            return retval
        elif task == "add_memory":
            tosend = part_to_memory(messages)
            client.add(messages=tosend[0], user_id=str(userid))
            client.add(messages=tosend[1], user_id=str(userid),infer=False,metadata={"type":"finance_advice"})
        elif task == "get_last_advice":
            res = client.search(query="",filters={"type":"finance_advice"},user_id=str(userid),limit=100)
            res = res.get("results",[])
            if len(res) > 0:
                maxmem = max(res,key=datesort)
                return maxmem.memory
            else:
                return ""
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
                        result = key_finance_advice(part.text)
                        vals['content'] = result
                        tosend[1].append(vals)
                    else:
                        tosend[0].append(vals)
    return tosend

def compare_advice(advice,prevadvice):
    system_prompt = '''
    You are a financial recommendation comparison assistant. Your task is to compare two pieces of financial advice and highlight the key differences.

    ### Guidelines
    - NEVER change the advice given , just compare new advice with previous advice and highlight the key differences.
    - ALWAYS append the differences at the end of the given advice
    - ALWAYS advice is provided with the format:
        Result -
    - **ALWAYS, When a new piece of financial advice (e.g., fund allocation) is generated and a previous one exists, do the following:**
        - Compare the new advice with the previous one.
        - Highlight key differences in:
            - Fund names
            - Fund categories (e.g., Large Cap vs Mid Cap)
            - Allocation percentages
            - Risk profiles or durations (if changed)
            - Absolute monetary difference (based on a known monthly savings amount)
            - Explain in simple language why the recommendation changed
            - Risk profiles or durations (if changed)
            - Absolute monetary difference (based on a known monthly savings amount)
            - Explain in simple language why the recommendation changed
    '''
    try:
        client = genai.Client()
        config = types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(
                thinking_budget=-1  # Dynamic thinking
            ),
            response_mime_type="application/json",
        )
        
        contents = [
            types.Content(
                role="user", parts=[types.Part(text=f"{system_prompt}")]
            ),
            types.Content(
                role="user", parts=[types.Part(text=f"{advice}")]
            ),
            types.Content(
                role="user", parts=[types.Part(text=f"{prevadvice}")]
            )
        ]
        
        response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=contents,
        config=config
        )
        candidate = response.candidates[0]
        if candidate and candidate.content and candidate.content.parts:
            parts = candidate.content.parts[0]
            if parts.text:
                return parts.text
            return ""
    except Exception as e:
        logger.error(f"Error in compare_advice: {e}")
        return ""

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

            Example:
                Previous Advice:
                - Nippon India Large Cap Fund: 60% of monthly savings
                - ICICI Prudential Large Cap Fund: 40% of monthly savings

                New Advice:
                - Nippon India Mid Cap Fund: 70% of monthly savings
                - ICICI Prudential Mid Cap Fund: 30% of monthly savings
                Monthly Savings: ₹10,000
                
                Output should contain this along with the new advice:
                1. Fund Category Changed:
                - Large Cap ➝ Mid Cap
                - Indicates a shift from low-risk, stable growth to higher-risk, higher-return potential.

                2. Allocation Adjusted:
                - Nippon India: 60% ➝ 70% (+₹1,000)
                - ICICI Prudential: 40% ➝ 30% (−₹1,000)

                3. Explanation:
                - The shift to Mid Cap funds suggests the user is now comfortable with higher risk in pursuit of better returns, even for the same investment horizon. Mid Cap funds offer higher growth potential but come with increased volatility.



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
            print(f"Memory list: {memory_list}")
            for i in memory_list:
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

                print(f"Response: {response}")
                candidate = response.candidates[0]
                parts = candidate.content.parts
                print(f"Parts: {parts}")

                # Check if we have a final result
                for part in parts:
                    if part.text and part.text.startswith("Result -"):
                        finalans = part.text
                        prev_advice = memory("get_last_advice",userid)
                        if len(prev_advice) > 0:
                            finalans = compare_advice(part.text,prev_advice)
                        contents.append(types.Content(
                            role="user",
                            parts=[types.Part(text=finalans)]
                        ))
                        memory("add_memory",userid,contents)
                        return finalans
                    
                    if part.function_call:
                        name = part.function_call.name
                        args = dict(part.function_call.args)  # Convert to dict
                        print(f"Calling tool: {name} with args: {args}")
                        result = call_tool(name, args)
                        print(f"Tool result obtained",len(result))
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
        result = get_finance_advice("I got laid off from my job, I get only a salary of 30000 with total expenses as 5000, My age is now 30 and I want to save as much as I can by 50",2)
        # result = analyze_user_profile("I got laid off from my job, I get only a salary of 30000 with total expenses as 5000, My age is now 30 and I want to save as much as I can by 50")
        print(result)
    except Exception as e:
        logger.error(f"Error running finance advisor: {e}")