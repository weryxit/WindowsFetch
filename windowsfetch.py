import platform
import os
import subprocess
import socket
from itertools import zip_longest
import ctypes
from datetime import datetime
import configparser
import re
import shutil
import requests
import json
import zipfile
import io
from typing import Optional, List, Dict, Any

__version__ = "1.1"
GITHUB_REPO = "weryxit/WindowsFetch"
GITHUB_RELEASES_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases"

# ------------------- GitHub Updater -------------------
def parse_version_from_tag(tag: str) -> Optional[str]:
    """Extract version number from tag string."""
    m = re.search(r"(\d+(?:\.\d+)+)", tag)
    return m.group(1) if m else None


def version_compare(v1: str, v2: str) -> int:
    """Compare two version strings numerically."""
    parts1 = [int(x) for x in v1.split(".")]
    parts2 = [int(x) for x in v2.split(".")]
    for a, b in zip(parts1, parts2):
        if a != b:
            return a - b
    return len(parts1) - len(parts2)


def check_github_for_update():
    """Check GitHub releases for a newer version and prompt user for update.

    This looks for a zip asset in the release first. If found, it will
    be used to update (extracted). If not found, the updater falls back
    to downloading raw files from the tag.
    """
    try:
        resp = requests.get(GITHUB_RELEASES_URL, timeout=5)
        resp.raise_for_status()
        releases = resp.json()
    except Exception:
        return False

    newest, newest_tag, newest_zip = None, None, None
    for rel in releases:
        tag = rel.get("tag_name") or rel.get("name") or ""
        ver = parse_version_from_tag(tag)
        if not ver:
            continue
        if newest is None or version_compare(ver, newest) > 0:
            newest, newest_tag = ver, tag
            # look for a zip asset
            for asset in rel.get("assets", []):
                if isinstance(asset, dict) and asset.get("name", "").lower().endswith('.zip'):
                    newest_zip = asset.get("browser_download_url")

    if newest and version_compare(newest, __version__) > 0:
        print(f"A new version of WindowsFastFetch is available: {newest} (tag: {newest_tag}).")
        ans = input("Do you want to update now? (y/n): ").strip().lower()
        if ans == "y":
            perform_update(newest_tag, newest_zip)
            print("Update complete. Please reapply custom modifications and reinstall using install.bat.")
            exit(0)
        else:
            print("Skipping update. Continuing with current version.")


def perform_update(tag: str, zip_url: Optional[str] = None):
    """Download and apply update.

    If zip_url is provided, download and extract the zip into the current
    script directory (overwriting). Otherwise fall back to downloading raw
    windowsfetch.py and wfconfig.conf from the tag path on GitHub.
    """
    here = os.path.dirname(os.path.abspath(__file__))
    cur_py = os.path.join(here, "windowsfetch.py")
    old_py = os.path.join(here, "windowsfetch_old.py")

    cfg_dir = os.path.join(os.environ.get("ProgramData", "C:\\"), "WindowsFetch")
    cfg_path = os.path.join(cfg_dir, "wfconfig.conf")
    cfg_old = os.path.join(cfg_dir, "wfconfig_old.conf")
    os.makedirs(cfg_dir, exist_ok=True)

    # Backup existing files
    try:
        if os.path.exists(cur_py):
            shutil.move(cur_py, old_py)
        if os.path.exists(cfg_path):
            shutil.move(cfg_path, cfg_old)
    except Exception as e:
        print("Error creating backups:", e)

    if zip_url:
        try:
            resp = requests.get(zip_url, timeout=20)
            resp.raise_for_status()
            with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
                # Extract into 'here' but avoid extracting files outside the directory
                for member in z.namelist():
                    # Normalize path
                    member_path = os.path.normpath(member)
                    if member_path.startswith('..'):
                        continue
                    # Join and ensure path stays inside 'here'
                    dest_path = os.path.join(here, *member_path.split('/'))
                    # Create directories as needed
                    if member.endswith('/'):
                        os.makedirs(dest_path, exist_ok=True)
                    else:
                        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                        with z.open(member) as src, open(dest_path, 'wb') as out:
                            out.write(src.read())
        except Exception as e:
            print("Error downloading/extracting ZIP update:", e)
            # restore backups
            if os.path.exists(old_py) and not os.path.exists(cur_py):
                shutil.move(old_py, cur_py)
            if os.path.exists(cfg_old) and not os.path.exists(cfg_path):
                shutil.move(cfg_old, cfg_path)
            return
    else:
        # Fallback: pull raw files from tag
        new_py_url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/{tag}/windowsfetch.py"
        new_cfg_url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/{tag}/wfconfig.conf"
        try:
            new_code = requests.get(new_py_url, timeout=10).text
            with open(cur_py, "w", encoding="utf-8") as f:
                f.write(new_code)
        except Exception as e:
            print("Error downloading new script:", e)
            if os.path.exists(old_py) and not os.path.exists(cur_py):
                shutil.move(old_py, cur_py)
            return

        try:
            cfg_data = requests.get(new_cfg_url, timeout=10).text
            with open(cfg_path, "w", encoding="utf-8") as f:
                f.write(cfg_data)
        except Exception as e:
            print("Error downloading new config:", e)
            if os.path.exists(cfg_old) and not os.path.exists(cfg_path):
                shutil.move(cfg_old, cfg_path)


# ------------------- WindowsFastFetch Class -------------------
class WindowsFastFetch:
    def __init__(self):
        self.colors = {'reset': '\033[0m', 'white': '\033[97m'}

        self.themes = {
            "purple": ['\033[38;5;183m','\033[38;5;177m','\033[38;5;171m','\033[38;5;165m','\033[38;5;129m','\033[38;5;99m','\033[38;5;63m','\033[38;5;60m'],
            "skyblue": ['\033[38;5;117m','\033[38;5;123m','\033[38;5;159m','\033[38;5;195m','\033[38;5;153m','\033[38;5;111m','\033[38;5;75m','\033[38;5;39m'],
            "blood-red": ['\033[38;5;52m','\033[38;5;88m','\033[38;5;124m','\033[38;5;160m','\033[38;5;196m','\033[38;5;202m','\033[38;5;208m','\033[38;5;214m'],
            "matrix": ['\033[38;5;22m','\033[38;5;28m','\033[38;5;34m','\033[38;5;40m','\033[38;5;46m','\033[38;5;82m','\033[38;5;118m','\033[38;5;154m'],
            "sunset": ['\033[38;5;226m','\033[38;5;220m','\033[38;5;214m','\033[38;5;208m','\033[38;5;202m','\033[38;5;196m','\033[38;5;160m','\033[38;5;129m'],
            "default": ['\033[38;5;250m','\033[38;5;251m','\033[38;5;252m','\033[38;5;253m','\033[38;5;254m','\033[38;5;255m']
        }

        self.ascii_art = [
            "            ......                      ",
            "         ......::...........            ",
            "     .......... ....   ........         ",
            "   ........ .  ......       ....        ",
            "   ...:... .. .:....:.  ..   ...::...   ",
            "   .:.... ..  ......... ..   .......... ",
            "   ..... .....:.. .......... ..:  .. .. ",
            "  ....:  .. ..:....:......:  ....  .... ",
            "  .:...  .....:  . :... ..:.  ...  ..   ",
            "  ...:.  ....:::.  .. ....:.  :......   ",
            "     . ....:++==:     -++++-. :::.:.    ",
            "     ..:..:.            ......:.....    ",
            "     .:..::.                ........    ",
            "     ......:... .......  ...:.... ..    ",
            "  ....... .:..:..:....:...:.   :. ..    ",
            "......... .:. :...:...:...:.  .:. ..    ",
            "..     .: .:.....:.......:.  ..:. .:    ",
            " ... ...:. ::-. .......  ..  .... .:.   ",
            "  ........ .:::. .  .. .:.  .:... .:.   ",
            "       ... ...::.. ....::.  ....:  :.   ",
            "      .........:::.:::::.  .. ..:. ..   ",
            " ",
        ]

        self._cache: Dict[str, str] = {}
        self.start_time = datetime.now()
        self.config = self.load_config()
        theme_name = self.config.get("settings", "color_theme", fallback="purple").lower()

        try:
            self.gradient_enabled = self.config.getboolean("settings", "gradient", fallback=True)
        except Exception:
            self.gradient_enabled = True

        self.gradient_colors = self.themes.get(theme_name, self.themes["default"])

    def load_config(self) -> configparser.ConfigParser:
        path = os.path.join(os.environ.get("ProgramData", "C:\\"), "WindowsFetch", "wfconfig.conf")
        cfg = configparser.ConfigParser()
        if not os.path.exists(path):
            cfg["settings"] = {"color_theme": "purple", "gradient": "True"}
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                cfg.write(f)
        else:
            cfg.read(path, encoding="utf-8")
        return cfg

    def gradient_text(self, text: str, colors: Optional[List[str]] = None) -> str:
        if not self.gradient_enabled:
            return f"{self.gradient_colors[0]}{text}{self.colors['reset']}"
        if colors is None:
            colors = self.gradient_colors
        result, segment_length = "", max(1, len(text) // len(colors))
        for i, ch in enumerate(text):
            color_index = min(i // segment_length, len(colors) - 1)
            result += f"{colors[color_index]}{ch}{self.colors['reset']}"
        return result

    def colorize(self, text: str, color: str) -> str:
        return f"{color}{text}{self.colors['reset']}"

    def run_ps_cached(self, command: str, timeout: int = 6) -> Optional[str]:
        if command in self._cache:
            return self._cache[command]
        try:
            proc = subprocess.run(
                ['powershell', '-NoProfile', '-Command', command],
                capture_output=True, text=True, encoding='utf-8', timeout=timeout
            )
            if proc.returncode == 0:
                out = proc.stdout.strip()
                self._cache[command] = out
                return out
        except Exception:
            return None
        return None

    def get_fast_info(self) -> Dict[str, str]:
        ps_script = r"""
            $os = Get-CimInstance Win32_OperatingSystem
            $cpu = (Get-CimInstance Win32_Processor | Select-Object -First 1).Name
            $gpus = Get-CimInstance Win32_VideoController | Select-Object Name,AdapterCompatibility,PNPDeviceID,AdapterRAM,VideoProcessor
            $total = [math]::Round($os.TotalVisibleMemorySize/1MB,1)
            $free = [math]::Round($os.FreePhysicalMemory/1MB,1)
            $used = $total - $free
            $battery = Get-CimInstance Win32_Battery | Select-Object -First 1

            $obj = [ordered]@{
                OS = $os.Caption
                CPU = $cpu
                RAM = ("{0}/{1} GB" -f $used, $total)
                GPUs = $gpus
            }

            if ($battery) {
                $pct = $battery.EstimatedChargeRemaining
                $status = if ($battery.BatteryStatus -in 2,6) { 'Charging' } else { 'Discharging' }
                $obj.Battery = ("{0}% [{1}]" -f $pct, $status)
            } else {
                $obj.Battery = "No Battery"
            }

            $obj | ConvertTo-Json -Compress
        """

        output = self.run_ps_cached(ps_script)
        info: Dict[str, str] = {
            "Host": socket.gethostname(),
            "User": os.environ.get('USERNAME', 'Unknown'),
            "Resolution": f"{ctypes.windll.user32.GetSystemMetrics(0)}x{ctypes.windll.user32.GetSystemMetrics(1)}",
        }

        if not output:
            info.update({"OS": f"Windows {platform.release()}", "CPU": platform.processor(), "RAM": "Unknown", "GPU": "Unknown", "Battery": "Unknown"})
            info["Fetch Version"] = __version__
            info["Theme"] = self.config.get("settings", "color_theme", fallback="purple")
            info["Gradient"] = "On" if self.gradient_enabled else "Off"
            return info

        try:
            parsed = json.loads(output)
        except Exception:
            parsed = {}

        if isinstance(parsed, dict):
            if 'OS' in parsed: info['OS'] = parsed.get('OS')
            if 'CPU' in parsed: info['CPU'] = parsed.get('CPU')
            if 'RAM' in parsed: info['RAM'] = parsed.get('RAM')
            info['Battery'] = parsed.get('Battery', 'No Battery')

            raw_gpus = parsed.get('GPUs', None)
            gpus_list: List[Dict[str, Any]] = []
            if isinstance(raw_gpus, list):
                gpus_list = raw_gpus
            elif isinstance(raw_gpus, dict):
                gpus_list = [raw_gpus]

            normalized = []
            for g in gpus_list:
                name = g.get('Name') or g.get('Caption') or str(g)
                vendor = g.get('AdapterCompatibility') or ''
                pnp = g.get('PNPDeviceID') or ''
                adapterram = g.get('AdapterRAM')
                try:
                    vramb = int(adapterram) if adapterram not in (None, '') else 0
                except Exception:
                    vramb = 0
                normalized.append({'name': name, 'vendor': vendor, 'pnp': pnp, 'adapterram': vramb})

            if not normalized:
                info['GPU'] = "Unknown"
            else:
                sorted_gpus = sorted(normalized, key=lambda x: x['adapterram'] or 0, reverse=True)
                if len(sorted_gpus) == 1:
                    g = sorted_gpus[0]
                    vram_mb = round(g['adapterram'] / (1024 ** 2), 1) if g['adapterram'] else 0
                    info['GPU'] = f"{g['name']} ({g['vendor']}) {vram_mb} MB"
                else:
                    discrete = sorted_gpus[0]
                    discrete_vram = round(discrete['adapterram'] / (1024 ** 2), 1) if discrete['adapterram'] else 0
                    info['GPU (Discrete)'] = f"{discrete['name']} ({discrete['vendor']}) {discrete_vram} MB"
                    for other in sorted_gpus[1:]:
                        vram_mb = round(other['adapterram'] / (1024 ** 2), 1) if other['adapterram'] else 0
                        if re.search(r"intel", other['vendor'], re.I):
                            info['GPU (Integrated)'] = f"{other['name']} ({other['vendor']}) {vram_mb} MB"
                        elif re.search(r"amd|ati|radeon", other['vendor'], re.I) and 'GPU (Integrated)' not in info:
                            info['GPU (Integrated)'] = f"{other['name']} ({other['vendor']}) {vram_mb} MB"
                        else:
                            key = 'GPU (Other)'
                            idx = 2
                            while key in info:
                                key = f'GPU (Other {idx})'
                                idx += 1
                            info[key] = f"{other['name']} ({other['vendor']}) {vram_mb} MB"

        info['Fetch Version'] = __version__
        info['Theme'] = self.config.get("settings", "color_theme", fallback="purple")
        info['Gradient'] = "On" if self.gradient_enabled else "Off"
        return info

    def display(self):
        print("\033c", end="")
        info = self.get_fast_info()
        header = f"{info.get('User')}@{info.get('Host')}"
        header_line = self.gradient_text(header)
        header_sep = self.gradient_text("-" * len(header))

        max_key_len = max(len(k) for k in info.keys())
        info_lines = [f"{self.gradient_text(k.ljust(max_key_len))}: {self.colorize(info[k], self.colors['white'])}" for k in info.keys()]

        first_row = " ".join(f"{c}███{self.colors['reset']}" for c in self.gradient_colors[:4])
        second_row = " ".join(f"{c}███{self.colors['reset']}" for c in self.gradient_colors[4:]) if len(self.gradient_colors) > 4 else ""
        palette_rows = [first_row]
        if second_row:
            palette_rows.append(second_row)

        all_info = [header_line, header_sep] + info_lines + [""] + palette_rows

        for art_line, info_line in zip_longest(self.ascii_art, all_info, fillvalue=""):
            art_colored = self.gradient_text(art_line) if art_line else " " * 40
            print(f"{art_colored}   {info_line}")


# ------------------- Main Runner -------------------
def main():
    WindowsFastFetch().display()


if __name__ == "__main__":
    check_github_for_update()
    main()
