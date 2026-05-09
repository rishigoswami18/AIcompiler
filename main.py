from fastapi import FastAPI

app = FastAPI(title="build_a_crm_system_with_login_contacts_manageme")


@app.get("/")
def root():
    return {"app": "build_a_crm_system_with_login_contacts_manageme", "status": "ok"}
