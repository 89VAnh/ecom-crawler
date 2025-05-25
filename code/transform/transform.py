import pandas as pd
import logging

logger = logging.getLogger(__name__)


class Transform:
    def __init__(self, data, **kwargs):
        self.data = data
        self.actions = kwargs.get("actions", {})
        self.script = kwargs.get("script", "")
        self.df = pd.DataFrame(data)

    def process(self):
        try:
            df = self.df
            for field, action in self.actions.items():
                if isinstance(action, str):
                    df[field] = eval(action)
                else:
                    df[field] = action

            if self.script:
                # Execute the script in the local namespace with df available
                exec(self.script, {"df": df})

            return df.to_dict(orient="records")
        except Exception as e:
            logger.error(f"Error in transform process: {str(e)}")
            return self.data
