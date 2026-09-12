#!/usr/bin/env python3
"""
Hubitat Code Sync Tool

Automates uploading and compiling Groovy drivers, apps, and libraries
directly to a Hubitat Elevation controller on your local network.

Configuration:
  Reads connection details from .hubitat.json in the repository root:
  {
    "hubIp": "hubitat.lan",
    "username": "your_username",
    "password": "your_password",
    "ssl": false
  }

Usage:
  python3 scripts/hubitat_sync.py list
  python3 scripts/hubitat_sync.py push <file1.groovy> [file2.groovy ...]
  python3 scripts/hubitat_sync.py push-all
"""

import sys
import os
import re
import json
import argparse
import urllib.request
import urllib.parse
import http.cookiejar

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".hubitat.json")

class HubitatClient:
    def __init__(self, config_file=CONFIG_PATH):
        if not os.path.exists(config_file):
            raise FileNotFoundError(f"Configuration file '{config_file}' not found. Please create it first.")
        
        with open(config_file, "r") as f:
            self.config = json.load(f)
            
        self.hub_ip = self.config.get("hubIp", "").strip()
        if not self.hub_ip:
            raise ValueError("Configuration must specify 'hubIp'.")
            
        self.username = self.config.get("username", "").strip()
        self.password = self.config.get("password", "").strip()
        self.ssl = self.config.get("ssl", False)
        self.scheme = "https" if self.ssl else "http"
        self.base_url = f"{self.scheme}://{self.hub_ip}"
        
        self.cj = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cj))
        self._authenticated = False

    def login(self):
        if self._authenticated or not (self.username and self.password):
            return True
        
        login_url = f"{self.base_url}/login"
        post_data = urllib.parse.urlencode({
            "username": self.username,
            "password": self.password,
            "submit": "Login"
        }).encode("utf-8")
        
        req = urllib.request.Request(login_url, data=post_data, headers={"User-Agent": "HubitatSync/1.0"})
        try:
            with self.opener.open(req) as resp:
                if resp.status == 200:
                    self._authenticated = True
                    return True
        except Exception as e:
            raise ConnectionError(f"Failed to authenticate with Hubitat at {self.hub_ip}: {e}")
        return False

    def get_json(self, path):
        self.login()
        req = urllib.request.Request(f"{self.base_url}{path}")
        with self.opener.open(req) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def post_form(self, path, data):
        self.login()
        post_data = urllib.parse.urlencode(data).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}{path}",
            data=post_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        with self.opener.open(req) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def get_installed_drivers(self):
        return self.get_json("/hub2/userDeviceTypes")

    def get_installed_apps(self):
        return self.get_json("/hub2/userAppTypes")

    def get_installed_libraries(self):
        return self.get_json("/hub2/userLibraries")

    @staticmethod
    def identify_file(file_path):
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        # Check for Library
        lib_match = re.search(r"library\s*\(\s*.*?name:\s*[\"\']([^\"\']+)[\"\']", content, re.DOTALL)
        if lib_match:
            ns_match = re.search(r"namespace:\s*[\"\']([^\"\']+)[\"\']", content)
            return {
                "type": "library",
                "name": lib_match.group(1),
                "namespace": ns_match.group(1) if ns_match else "",
                "source": content
            }

        # Check for Driver vs App definition
        def_match = re.search(r"definition\s*\(\s*name:\s*[\"\']([^\"\']+)[\"\']", content)
        if def_match:
            name = def_match.group(1)
            ns_match = re.search(r"namespace:\s*[\"\']([^\"\']+)[\"\']", content)
            namespace = ns_match.group(1) if ns_match else ""

            # In Hubitat, drivers always wrap definition inside 'metadata { ... }'
            # Apps define 'definition(...)' directly at the top level
            has_metadata = bool(re.search(r"\bmetadata\s*\{", content))
            item_type = "driver" if has_metadata else "app"

            return {
                "type": item_type,
                "name": name,
                "namespace": namespace,
                "source": content
            }

        return None

    def push_file(self, file_path, dry_run=False):
        info = self.identify_file(file_path)
        if not info:
            print(f"[-] Could not identify component type or name in {file_path}")
            return False

        item_type = info["type"]
        name = info["name"]
        namespace = info["namespace"]
        source = info["source"]

        # Look up matching component on the hub
        target_id = None
        target_entry = None

        if item_type == "driver":
            drivers = self.get_installed_drivers()
            for d in drivers:
                if d.get("name") == name and (not namespace or d.get("namespace") == namespace):
                    target_id = d.get("id")
                    target_entry = d
                    break
            code_endpoint = f"/driver/ajax/code?id={target_id}"
            update_endpoint = "/driver/ajax/update"
        elif item_type == "app":
            apps = self.get_installed_apps()
            for a in apps:
                if a.get("name") == name and (not namespace or a.get("namespace") == namespace):
                    target_id = a.get("id")
                    target_entry = a
                    break
            code_endpoint = f"/app/ajax/code?id={target_id}"
            update_endpoint = "/app/ajax/update"
        elif item_type == "library":
            libs = self.get_installed_libraries()
            for l in libs:
                if l.get("name") == name and (not namespace or l.get("namespace") == namespace):
                    target_id = l.get("id")
                    target_entry = l
                    break
            code_endpoint = f"/library/ajax/code?id={target_id}"
            update_endpoint = "/library/ajax/update"
        else:
            print(f"[-] Unknown item type '{item_type}'")
            return False

        if not target_id:
            print(f"[-] {item_type.capitalize()} '{name}' (namespace: {namespace}) is not installed on hub {self.hub_ip}")
            return False

        print(f"[*] Found {item_type} '{name}' on hub -> ID: {target_id}")

        if dry_run:
            print(f"    [DRY-RUN] Would upload {len(source)} chars to {update_endpoint}")
            return True

        # Fetch current version token
        code_data = self.get_json(code_endpoint)
        current_version = code_data.get("version", 0)

        # Upload and compile
        result = self.post_form(update_endpoint, {
            "id": target_id,
            "version": current_version,
            "source": source
        })

        status = result.get("status")
        if status == "success":
            new_version = result.get("version", current_version + 1)
            print(f"[+] Successfully compiled & updated '{name}' on Hubitat! (New version: {new_version})")
            return True
        else:
            err = result.get("errorMessage", "Unknown compiler error")
            print(f"[!] COMPILATION ERROR on Hubitat for '{name}':")
            print(f"    {err}")
            return False


def main():
    parser = argparse.ArgumentParser(description="Hubitat Elevation Code Sync & Compiler Tool")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # list command
    subparsers.add_parser("list", help="List all Govee drivers, apps, and libraries on the hub")

    # push command
    push_parser = subparsers.add_parser("push", help="Push one or more local Groovy files to the hub")
    push_parser.add_argument("files", nargs="+", help="Path to .groovy files to upload")
    push_parser.add_argument("--dry-run", action="store_true", help="Simulate without uploading")

    # push-all command
    subparsers.add_parser("push-all", help="Push all modified or Govee files found in repo")

    args = parser.parse_args()

    try:
        client = HubitatClient()
    except Exception as e:
        print(f"[!] Configuration error: {e}")
        sys.exit(1)

    if args.command == "list":
        print(f"Connecting to Hubitat at {client.hub_ip}...")
        client.login()

        print("\n=== INSTALLED GOVEE DRIVERS ===")
        for d in client.get_installed_drivers():
            if "govee" in (d.get("name", "") + d.get("namespace", "")).lower():
                print(f"  [{d.get('id'):<5}] {d.get('name')} (ns: {d.get('namespace')})")

        print("\n=== INSTALLED GOVEE APPS ===")
        for a in client.get_installed_apps():
            if "govee" in (a.get("name", "") + a.get("namespace", "")).lower():
                print(f"  [{a.get('id'):<5}] {a.get('name')} (ns: {a.get('namespace')})")

        print("\n=== INSTALLED GOVEE LIBRARIES ===")
        for l in client.get_installed_libraries():
            if "govee" in (l.get("name", "") + l.get("namespace", "")).lower():
                print(f"  [{l.get('id'):<5}] {l.get('name')} (ns: {l.get('namespace')})")

    elif args.command == "push":
        success = True
        for f in args.files:
            if not os.path.exists(f):
                print(f"[-] File not found: {f}")
                success = False
                continue
            res = client.push_file(f, dry_run=args.dry_run)
            if not res:
                success = False
        sys.exit(0 if success else 1)

    elif args.command == "push-all":
        repo_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        govee_v2_dir = os.path.join(repo_dir, "Govee", "v2")
        files_to_push = [
            # Libraries first
            os.path.join(govee_v2_dir, "Mavrrick.Govee_Cloud_API.groovy"),
            os.path.join(govee_v2_dir, "Mavrrick.Govee_Cloud_RGB.groovy"),
            os.path.join(govee_v2_dir, "Mavrrick.Govee_Cloud_Level.groovy"),
            os.path.join(govee_v2_dir, "Mavrrick.Govee_LAN_API.groovy"),
            os.path.join(govee_v2_dir, "Mavrrick.Govee_Cloud_MQTT.groovy"),
            os.path.join(govee_v2_dir, "Mavrrick.Govee_Cloud_Life.groovy"),
            # Parent App
            os.path.join(govee_v2_dir, "Mavrrick.GoveeIntegrationv2.groovy"),
            # Main Driver
            os.path.join(govee_v2_dir, "Mavrrick.Goveev2ColorLights3Driver.groovy")
        ]
        for f in files_to_push:
            if os.path.exists(f):
                client.push_file(f)

if __name__ == "__main__":
    main()
