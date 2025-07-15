from fastapi import FastAPI
import supabase_connector

app = FastAPI()

#To be called by the cron job and to store values
@app.get("/run_scapre")
async def run_scapre():
    try:
        value = supabase_connector.update_details()
        if value["status"] == 200:
            return {"message":"Data updated successfully"},200
        else:
            return {"message":"Data not updated"},400
    except Exception as e:
        return {"message": f"Error: {e}"},400

@app.get("/get_details/{info}")
async def get_details(info:str):
    try:
        value = supabase_connector.get_details(info)
        if value["status"] == 200:
            return {"message":"Data fetched successfully","data":value["data"]},200
        else:
            return {"message":"Data not fetched"},400
    except Exception as e:
        return {"message": f"Error: {e}"},400

@app.get("/")
async def root():
    return {"message":"Hello World"}
