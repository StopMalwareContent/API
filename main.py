import os
from datetime import timedelta, datetime
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from authx import AuthX, AuthXConfig
from models.site import IllegalSite
from config.database import collection_name
from schema.schemas import site_entities
from dotenv import load_dotenv
from api_analytics.fastapi import Analytics

app = FastAPI(title="StopMalwareContent API", description="The official API for StopMalwareContent Extension.", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(Analytics, api_key=os.getenv("ANALYTICS_API_KEY"))

load_dotenv()

config = AuthXConfig(
     JWT_ALGORITHM = "HS256",
     JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY"),
     JWT_TOKEN_LOCATION = ["headers"],
)

auth = AuthX(config=config)
auth.handle_errors(app)


@app.get('/')
def root():
  return {
    "message": "If you are reading this, StopMalwareContent API is alive.",
  }


@app.get('/login')
def login(username: str, password: str):
  if username == os.getenv("MASTER_USER") and password == os.getenv("MASTER_PASSWORD"):
    current_time = datetime.now()

    time_in_24hours = current_time + timedelta(seconds=24 * 60 * 60)

    token = auth.create_access_token(uid=username, expiry=time_in_24hours)
    return {"access_token": token}
  raise HTTPException(401, detail={"message": "Invalid credentials"})


@app.get("/sites")
async def get_sites() -> list[IllegalSite]:
  sites = site_entities(collection_name.find())
  return sites


@app.get("/sites/{domain}")
async def get_site(domain) -> list[IllegalSite]:
  site = site_entities(collection_name.find({"domain": domain}))
  return site


@app.post("/sites", dependencies=[Depends(auth.access_token_required)])
async def post_site(site: IllegalSite):
  collection_name.insert_one(dict(site))


@app.put("/sites/{domain}", dependencies=[Depends(auth.access_token_required)])
async def put_site(domain: str, site: IllegalSite):
  collection_name.find_one_and_update({"domain": domain}, {"$set": dict(site)})


@app.delete("/sites/{domain}", dependencies=[Depends(auth.access_token_required)])
async def delete_site(domain: str):
  collection_name.find_one_and_delete({"domain": domain})


@app.get("/stats")
async def get_stats():
  sites = site_entities(collection_name.find())
  return {
    "sites": len(list(sites))
  }