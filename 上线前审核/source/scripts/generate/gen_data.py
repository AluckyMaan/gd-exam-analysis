import json

d = json.load(open('tumu_data.json', encoding='utf-8'))
details = d['details']

# Build ALL_POSITIONS JS array
items = []
for item in details:
    y = item["year"]
    u = item["unit"].replace("\\", "\\\\").replace("\"", "\\\"")
    p = item["position"].replace("\\", "\\\\").replace("\"", "\\\"")
    n = item["recruits"]
    c = item["city"].replace("\\", "\\\\").replace("\"", "\\\"")
    e = item["education"].replace("\\", "\\\\").replace("\"", "\\\"")
    f = "true" if item["fresh_only"] else "false"
    pr = item.get("prof_fields", "").replace("\\", "\\\\").replace("\"", "\\\"")
    items.append(f'{{"y":"{y}","u":"{u}","p":"{p}","n":{n},"c":"{c}","e":"{e}","f":{f},"pr":"{pr}"}}')

all_pos = "var ALL_POSITIONS = [\n" + ",\n".join(items) + "\n];"
print(f"// Generated {len(details)} positions, {len(all_pos)} chars")
print("Done")
