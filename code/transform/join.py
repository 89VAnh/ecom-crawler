import pandas as pd
import json

def process(data):
    price = data["price"]["Data"]["Data"]
    statistic = data["statistic"]["Data"]["Data"]
    khoingoai = data["khoingoai"]["Data"]["Data"]
    tudoanh = data["tudoanh"]["Data"]["Data"]["ListDataTudoanh"]
    
    
    price_df = pd.DataFrame(price)
    statis_df = pd.DataFrame(statistic)
    khoingoai_df = pd.DataFrame(khoingoai)
    tudoanh_df = pd.DataFrame(tudoanh)

    price_df = price_df.rename(columns={"Ngay": "Date"})
    khoingoai_df = price_df.rename(columns={"Ngay": "Date"})
    result = pd.merge(price_df, statis_df, on="Date", how="outer")
    result = pd.merge(result, khoingoai_df, on="Date", how = "outer")
    result = pd.merge(result, tudoanh_df, on = "Date", how = "outer")
    result_json = json.dumps(result.to_dict(orient="records"))
    return result_json