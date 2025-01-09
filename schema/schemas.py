def site_entity(site) -> dict:
  return {
    "id": str(site["_id"]),
    "domain": site["domain"],
    "notes": site["notes"],
    "path": site["path"],
    "reason": site["reason"]
  }


def site_entities(sites) -> list:
  return (site_entity(site) for site in sites)
