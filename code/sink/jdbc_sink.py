import jaydebeapi


class JDBCSink():
    def __init__(self, data, **kawgs):
        self.data = data
        self.kwargs = kawgs
    
    def execute(self):
        driver_class = self.kwargs.get("class")
        jdbc_url = self.kwargs.get("url")
        username = self.kwargs.get("username")
        password = self.kwargs.get("password")
        jdbc_driver = self.kwargs.get("driver")
        table = self.kwargs.get("table")
        fields = self.kwargs.get("fields")
        
        conn = jaydebeapi.connect(
            driver_class,
            jdbc_url,
            [username, password],
            jdbc_driver
        )
        
        cursor = conn.cursor()
        field_text = ",".join(fields)
        insert_fields = ",".join(["?" for i in range(fields)])
        insert_cmd = f"INSERT INTO {table} ({field_text}) VALUES ({insert_fields})"
        insert_data = [(row.get(field) for field in fields) for row in self.data]
        cursor.executemany(insert_cmd, insert_data)
        conn.commit()
        cursor.close()
        conn.close()