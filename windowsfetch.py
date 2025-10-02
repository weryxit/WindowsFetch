import platform
import os
import subprocess
import socket
from itertools import zip_longest
import ctypes
from datetime import datetime

class WindowsFastFetch:
    def __init__(self):
        self.colors = {
            'reset': '\033[0m',
            'purple_light': '\033[38;5;147m',
            'purple_medium': '\033[38;5;141m',
            'purple_dark': '\033[38;5;135m',
            'purple_deep': '\033[38;5;129m',
            'purple_violet': '\033[38;5;99m',
            'purple_magenta': '\033[38;5;165m',
            'purple_lavender': '\033[38;5;183m',
            'accent_cyan': '\033[38;5;117m',
            'accent_pink': '\033[38;5;213m',
            'white': '\033[97m',
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
        ]
        self._cache = {}
        self.gradient_colors = ['purple_light', 'purple_medium', 'purple_dark', 'purple_deep', 'purple_violet']
        self.start_time = datetime.now()

    def colorize(self, text, color):
        return f"{self.colors.get(color, '')}{text}{self.colors['reset']}"
    
    def show_color_palette(self):
        colors_to_show = [
            'purple_light', 'purple_medium', 'purple_dark', 
            'purple_deep', 'purple_violet', 
            'accent_cyan', 'accent_pink', 'white'
        ]
        palette_line = ""
        for c in colors_to_show:
            palette_line += self.colorize("███", c) + " "
        print("\n" + palette_line + "\n")


    def gradient_text(self, text, colors=None):
        if colors is None:
            colors = self.gradient_colors
        result = ""
        segment_length = max(1, len(text) // len(colors))
        for i, char in enumerate(text):
            color_index = min(i // segment_length, len(colors) - 1)
            result += self.colorize(char, colors[color_index])
        return result

    def gradient_label(self, label, value):
        return f"{self.gradient_text(label+': ', ['purple_light','accent_cyan'])}{self.colorize(value,'white')}"

    def run_ps_cached(self, command):
        if command in self._cache:
            return self._cache[command]
        try:
            result = subprocess.run(
                ['powershell', '-Command', command],
                capture_output=True, text=True, encoding='utf-8', timeout=3
            )
            if result.returncode == 0:
                output = result.stdout.strip()
                self._cache[command] = output
                return output
        except:
            pass
        return None

    def get_fast_info(self):
        return {
            "OS": self.get_os_info(),
            "Host": self.get_host_info(),
            "Processes": self.get_processes(),
            "Resolution": self.get_resolution(),
            "CLR Version": self.run_ps_cached("[System.Environment]::Version.ToString()") or "N/A",
            "Uptime": self.get_uptime(),
            "RAM": self.get_memory(),
            "CPU": self.get_cpu_info(),
            "GPU": self.get_gpu_info(),
            "User": self.get_user_info(),
            "Root Dir": os.environ.get("SystemRoot", "C:\\Windows"),
        }

    def get_os_info(self):
        return self.run_ps_cached("(Get-CimInstance Win32_OperatingSystem).Caption") or f"Windows {platform.release()}"

    def get_host_info(self):
        return socket.gethostname()

    def get_user_info(self):
        return os.environ.get('USERNAME', 'Unknown')

    def get_uptime(self):
        try:
            tick = ctypes.windll.kernel32.GetTickCount64()
            secs = tick // 1000
            d,h,m = secs//86400,(secs%86400)//3600,(secs%3600)//60
            return f"{d}d {h}h {m}m" if d else f"{h}h {m}m"
        except:
            return "Unknown"

    def get_cpu_info(self):
        return self.run_ps_cached("(Get-CimInstance Win32_Processor).Name") or platform.processor()

    def get_gpu_info(self):
        return self.run_ps_cached("(Get-CimInstance Win32_VideoController).Name") or "Unknown"

    def get_memory(self):
        return self.run_ps_cached(
            "$m=Get-CimInstance Win32_OperatingSystem; '{0}/{1} GB' -f "
            "[math]::Round(($m.TotalVisibleMemorySize-$m.FreePhysicalMemory)/1MB,1),"
            "[math]::Round($m.TotalVisibleMemorySize/1MB,1)"
        ) or "Unknown"

    def get_disk(self):
        return self.run_ps_cached(
            "$d=Get-CimInstance Win32_LogicalDisk -Filter \"DeviceID='C:'\"; '{0}/{1} GB' -f "
            "[math]::Round(($d.Size-$d.FreeSpace)/1GB,1),"
            "[math]::Round($d.Size/1GB,1)"
        ) or "Unknown"

    def get_resolution(self):
        try:
            u=ctypes.windll.user32
            return f"{u.GetSystemMetrics(0)}x{u.GetSystemMetrics(1)}"
        except:
            return "Unknown"

    def get_terminal(self):
        return "Windows Terminal" if 'WT_SESSION' in os.environ else "CMD"

    def get_network(self):
        try:
            return socket.gethostbyname(socket.gethostname())
        except:
            return "Unknown"

    def get_processes(self):
        try:
            res=subprocess.check_output("tasklist /fo csv | find /c /v \"\"",shell=True,text=True)
            return res.strip()
        except:
            return "Unknown"

    def display(self):
        print("\033c", end="")

        info = self.get_fast_info()

        header = f"{self.get_user_info()}@{self.get_host_info()}"
        print(self.gradient_text(header))
        print("-" * len(header))

        max_key_len = max(len(k) for k in info.keys())
        info_lines = [f"{self.gradient_text(k.ljust(max_key_len))}: {self.colorize(v,'white')}" for k, v in info.items()]

        for art_line, info_line in zip_longest(self.ascii_art, info_lines, fillvalue=""):
            art_colored = self.gradient_text(art_line) if art_line else " " * 40
            print(f"{art_colored}   {info_line}")

        self.show_color_palette()

        print("\n" + self.gradient_text(" Made with 💜 by Werzyk "))

def main():
    WindowsFastFetch().display()

if __name__=="__main__":
    main()

"""self.ascii_art = [
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
        ]"""