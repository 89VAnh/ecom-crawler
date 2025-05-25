from datetime import datetime, timezone

now = datetime.now().replace(tzinfo=timezone.utc)

print(now)
print(now.strftime("%Y-%m-%d %H:%M:%S"))
print(datetime.strptime("20250505182003", "%Y%m%d%H%M%S"))
