from fastapi import FastAPI, HTTPException
import numpy as np
import joblib
from pydantic import BaseModel
import example_model

app = FastAPI()

model = joblib.load("iris_model.pkl")

class PredictionRequest(BaseModel):
    data: list

@app.post("/v0/predict/")
def model_endpoint(request: PredictionRequest):
    input_data = np.array(request.data)
    if input_data.ndim != 2 or input_data.shape[1] != 4: 
        raise HTTPException(status_code=400, detail="Invalid input shape. Expected 2D array with 4 features.")

    predictions = model.predict(input_data)

    return {"predictions": predictions.tolist()}
