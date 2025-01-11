import os, requests, json
from datetime import timedelta, datetime
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from authx import AuthX, AuthXConfig
from models.site import IllegalSite, ReportedIllegalSite
from config.database import sites_collection, reports_collection
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
  sites = site_entities(sites_collection.find())
  return sites


@app.get("/sites/{domain}")
async def get_site(domain) -> list[IllegalSite]:
  site = site_entities(sites_collection.find({"domain": domain}))
  return site


@app.post("/sites", dependencies=[Depends(auth.access_token_required)])
async def post_site(site: IllegalSite):
  sites_collection.insert_one(dict(site))

  requests.post(os.getenv("VERDICTS_DISCORD_WEBHOOK_URL"), json={
    "content": f"<:smc_flag:1327674316233379840> **A new website has been flagged**\n\nDomain: *{site.get('domain')}*\Reason: *{site.get('reason')}*"
  })


@app.put("/sites/{domain}", dependencies=[Depends(auth.access_token_required)])
async def put_site(domain: str, site: IllegalSite):
  sites_collection.find_one_and_update({"domain": domain}, {"$set": dict(site)})


@app.delete("/sites/{domain}", dependencies=[Depends(auth.access_token_required)])
async def delete_site(domain: str):
  sites_collection.find_one_and_delete({"domain": domain})

  requests.post(os.getenv("VERDICTS_DISCORD_WEBHOOK_URL"), json={
    "content": f"<:smc_unflag:1327676379331825745> **Website has been unflagged**\n\nDomain: *{domain}*"
  })


@app.get("/reports")
async def get_reports() -> list[IllegalSite]:
  sites = site_entities(reports_collection.find())
  return sites


@app.get("/reports/{domain}")
async def get_report(domain) -> list[IllegalSite]:
  site = site_entities(reports_collection.find({"domain": domain}))
  return site


@app.delete("/reports/{domain}", dependencies=[Depends(auth.access_token_required)])
async def delete_report(domain: str):
  reports_collection.find_one_and_delete({"domain": domain})


@app.post("/reports")
async def post_report(site: ReportedIllegalSite):
  r = requests.post("https://challenges.cloudflare.com/turnstile/v0/siteverify", data={
    "secret": os.getenv("TURNSTILE_SECRET_KEY"),
    "response": site.token
  })

  if json.loads(r.text)["success"]:
    site_dict = dict(site)
    site_dict.pop('token', None)

    if not reports_collection.find_one({"domain": site.domain}):

      match site_dict["reason"]:
        case "illegal-redistribution":
          hr_reason = "Illegal redistribution"
        case "phishing":
          hr_reason = "Phishing website"
        case "malware":
          hr_reason = "Contains malware"
        case "puw":
          hr_reason = "Potentially unwanted website"
        case "false-pos":
          hr_reason = "False positive"
        case _:
          raise HTTPException(400, "Invalid reason")

      site_dict["reason"] = hr_reason
      reports_collection.insert_one(site_dict)

      requests.post(os.getenv("REPORTS_DISCORD_WEBHOOK_URL"), json={
        "content": f"<:smc_bell:1327674323007307858> **A new website has been reported**\n\nDomain: *{site_dict.get('domain')}*\nReason: *{site_dict.get('reason')}*"
      })
    else:
      raise HTTPException(409, "Report already exists")
  else:
    raise HTTPException(400, "Invalid captcha")

@app.get("/stats")
async def get_stats():
  sites = site_entities(sites_collection.find())
  reports = site_entities(reports_collection.find())
  return {
    "sites": len(list(sites)),
    "reports": len(list(reports))
  }