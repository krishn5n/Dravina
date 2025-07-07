import scrape_data
from typing import List

# Get details about every mutual fund
def obtain_mutual_funds(tags: List[str]):
    try:
        setsearch = set(tags)
        retval = []
        fund_list = scrape_data.mutual_funds()
        # Add validation for fund_list
        if not fund_list:
            print("No mutual funds data available")
            return []
        
        for i in fund_list:
            # Add validation for fund structure
            if not isinstance(i, dict) or 'tags' not in i:
                print(f"Invalid fund structure: {i}")
                continue
                
            for j in i['tags']:
                if j in setsearch:
                    retval.append(i)
                    break
        
        return retval
    except Exception as e:
        print(f"Error in obtain_mutual_funds: {e}")
        return []

# Get information on stones
def obtain_stone_vals(option: str):  # Changed from int to str to match usage
    print("getting stone")
    try:
        list_val = scrape_data.gold_silver_details()
        
        if not list_val:
            print("No stone data available")
            return {}
        
        if option == '0':
            return list_val.get('gold', {})
        elif option == '1':
            return list_val.get('silver', {})
        return list_val
    except Exception as e:
        print(f"Error in obtain_stone_vals: {e}")
        return {}

# Get information on each fund types -> From an api
def obtain_fund_type_info(category: str, fund: str):
    print("Getting Fund types")
    try:
        details = scrape_data.mutual_fund_details()
        
        if not details:
            print("No fund details available")
            return {"result": "No fund details available from data source"}
        
        if category in details:
            if fund in details[category]:
                return {"result": f"{details[category][fund]}"}
            else:
                # List available funds in the category
                available_funds = list(details[category].keys()) if details[category] else []
                return {"result": f"The fund '{fund}' is not available in category '{category}'. Available funds: {available_funds}"}
        else:
            # List available categories
            available_categories = list(details.keys())
            return {"result": f"The category '{category}' does not exist. Available categories: {available_categories}"}
    except Exception as e:
        print(f"Error in obtain_fund_type_info: {e}")
        return {"result": f"Error retrieving fund information: {str(e)}"}
    