"""Add the freshly built IPA to the SideStore / AltStore source.

usage: update_source.py IPA SOURCE_JSON VERSION BUILD DOWNLOAD_URL REPO

The app's permissions are read from the IPA itself, because SideStore and
AltStore refuse to install an app whose permissions differ from the source.
"""
import datetime
import json
import os
import plistlib
import sys
import zipfile

ipa, source_path, version, build, download_url, repo = sys.argv[1:7]

with zipfile.ZipFile(ipa) as z:
    info_name = next(n for n in z.namelist()
                     if n.startswith("Payload/") and n.endswith(".app/Info.plist") and n.count("/") == 2)
    info = plistlib.loads(z.read(info_name))

bundle_id = info["CFBundleIdentifier"]
privacy = {k: v for k, v in info.items() if k.startswith("NS") and k.endswith("UsageDescription")}
raw = f"https://raw.githubusercontent.com/{repo}"

try:
    with open(source_path, encoding="utf-8") as f:
        source = json.load(f)
except (OSError, ValueError):
    source = {}

source.update({
    "name": "locbridge",
    "identifier": f"io.github.{repo.split('/')[0].lower()}.locbridge.source",
    "subtitle": "Builds of locbridge, straight from GitHub Actions.",
    "iconURL": f"{raw}/main/sidestore/icon.png",
    "website": f"https://github.com/{repo}",
    "tintColor": "#3B82F6",
})
source.setdefault("news", [])

apps = source.setdefault("apps", [])
app = next((a for a in apps if a.get("bundleIdentifier") == bundle_id), None)
if app is None:
    app = {"bundleIdentifier": bundle_id, "versions": []}
    apps.insert(0, app)
app.update({
    "name": info.get("CFBundleDisplayName", "locbridge"),
    "developerName": repo.split("/")[0],
    "subtitle": "Teleport your iPhone's location, on the phone itself.",
    "localizedDescription": (
        "Sets your iPhone's location from the phone itself, through Apple's developer "
        "location service. Needs LocalDevVPN. Built on Locus (MIT)."
    ),
    "iconURL": f"{raw}/main/sidestore/icon.png",
    "tintColor": "#3B82F6",
    "category": "utilities",
    # Unsigned builds carry no entitlements; SideStore adds its own when it signs.
    "appPermissions": {"entitlements": [], "privacy": privacy},
})

entry = {
    "version": version,
    "buildVersion": build,
    "marketingVersion": version,
    "date": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "downloadURL": download_url,
    "size": os.path.getsize(ipa),
    "minOSVersion": info.get("MinimumOSVersion", "18.0"),
    "localizedDescription": f"Build {build}.",
}
# Newest first: SideStore takes the first entry as the latest. Keep the last ten.
versions = [v for v in app.get("versions", []) if v.get("version") != version]
app["versions"] = [entry] + versions[:9]

with open(source_path, "w", encoding="utf-8") as f:
    json.dump(source, f, indent=2, ensure_ascii=False)
    f.write("\n")
print(f"{bundle_id} {version} ({build}) -> {source_path}")
