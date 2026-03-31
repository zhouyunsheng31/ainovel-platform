import main

print("FASTAPI_IMPORT_OK")
print("APP_TITLE=", main.app.title)
print("ROUTE_COUNT=", len([r for r in main.app.routes if hasattr(r, "path")]))
for r in main.app.routes:
    if hasattr(r, "path"):
        print("ROUTE=", r.path)
