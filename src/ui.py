import time
import threading
import importlib
import os
import sys
import subprocess
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.live import Live
from rich.align import Align
from rich.prompt import Prompt
from rich.layout import Layout
from rich.table import Table
from rich.theme import Theme
from rich.box import HEAVY
from rich.spinner import Spinner

EPISODE_ASCII_ART = r"""
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣠⣶⣿⣟⠷⣄⠀⠀⠀⠀⠀⠀⠀⣀⣴⣾⢿⣿⣿⠰⠀⠀⠀⣀⡴⣫⠴⡁⠀⠀⠀⣀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣀⣀⡀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⡾⠟⠛⠿⣻⣷⡀⢂⠀⠀⠀⠀⣠⣾⡟⢡⣴⣾⡿⢣⠁⠀⢀⣴⣿⠟⠫⣑⣴⣶⣿⣿⣷⣏⡑⠂⠀⠀⠀⠀⢀⣴⣿⡏⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣞⠁⣾⣷⢂⢻⣿⡅⢂⣠⢀⣤⣾⣿⣯⢰⣿⡛⠭⣘⣴⣿⣿⡿⠟⢁⡮⢟⣻⣿⡿⢿⣿⡿⣿⣧⣂⠀⣀⣠⣶⣿⣿⣿⣿⡄⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣿⣦⣿⠟⢠⣿⣿⠁⣢⣿⢧⣿⣿⣿⣿⣷⣷⡶⣳⣭⣭⣩⣬⣤⣾⡟⣾⣿⣿⠿⣿⣷⣦⣙⠻⣿⣿⣿⣿⣿⣿⣿⣿⠿⢏⠁⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⢉⣡⣾⣿⣿⣿⣿⠿⣟⣾⣿⢳⣨⣿⣿⡛⢇⣽⣿⣿⣿⣿⣿⣿⣧⠹⣿⣿⣶⠈⢿⣿⣿⣧⡉⢿⣿⣿⣽⣿⡷⢋⡈⣀⠀⠀
⠀⠀⠀⠀⡆⠀⠀⠀⠘⣦⡄⠀⠀⣰⣿⣿⣿⣿⢿⣻⣿⣿⣿⣿⣟⠘⣿⣿⣿⣿⣿⣿⣿⣿⣻⣽⣿⡿⣿⣷⣌⠉⠍⠃⢸⣿⣿⣿⡷⡈⢿⣿⣿⡏⣲⣿⡷⢍⣨⢒
⠀⠀⠨⠙⠃⠀⠀⠀⢸⣷⡏⠀⠸⣱⣾⣿⣷⣿⣿⣿⢻⣭⣛⡝⣉⣠⣿⣿⣿⣻⣿⣿⣽⣿⣿⢿⡷⡙⣿⣿⠿⣿⣿⣿⣿⣿⣿⣻⡟⢠⢹⣿⠯⢱⣴⡾⣱⡿⢿⣿
⠀⠀⠀⠀⠀⠀⠀⠀⢸⣿⡃⠄⣠⣿⣿⡟⣿⣿⣿⣿⠘⡜⢿⣿⣿⣿⣿⣿⣿⣿⠄⡻⢿⣿⣿⢛⡧⠀⣿⣿⣧⠛⢻⡛⠿⠿⠿⠟⠃⠄⢸⣿⠃⣿⣿⣣⠇⡸⢸⣿
⠀⠀⠀⠀⠀⠀⠀⠀⡏⢿⡅⢀⠙⢿⠇⣸⣿⣿⡷⠋⡀⠈⠀⡉⢛⠻⣛⡿⣽⠏⠀⠀⠘⣿⡏⠰⠂⢁⣿⣧⡙⠿⣶⣌⠁⠊⠀⠂⢁⣠⣾⢁⠞⣿⣿⣿⡾⢃⣾⣿
⠀⠀⠀⠀⠀⠀⠀⠀⠜⠸⣿⣶⣤⡾⡀⣏⣿⡗⠠⠑⢀⣴⣿⣶⣄⡁⢈⠀⠁⠀⣰⢎⢸⡟⠀⠡⠀⣺⣿⣿⡟⣰⣤⣤⣤⣴⣾⣿⣿⣿⣿⣼⣼⣿⣟⣶⣶⡿⠛⢉
⠀⠀⠀⠀⠀⠀⠀⠀⠈⢂⠌⠛⠊⠑⢠⠃⡿⠀⠄⣰⣿⣿⣿⣿⣿⠏⢀⡰⢶⣫⠗⠫⠎⠀⢈⣀⠐⢈⠻⡼⣗⠰⡿⣿⠁⡿⢋⡝⠶⣛⠿⢻⠿⠟⣡⢿⢫⣴⣿⣿
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣈⡤⢐⠀⠤⠘⡐⠀⢰⣯⢟⡩⣬⠛⢊⡎⡀⠩⣤⣄⣤⣥⡀⣴⢾⣻⣟⣄⠈⡕⢃⠸⢡⠋⡀⠁⠃⠌⠴⣁⠚⢤⡠⡴⣽⡿⣼⣿⣿⣿
⠀⠀⠀⠀⠀⠀⠀⠀⣠⡾⠟⠙⠂⠀⠂⠄⠐⠀⡞⣭⢆⠾⠜⣼⠟⢀⠀⣠⣿⣿⣿⣿⢻⣭⣿⣳⢟⡾⠀⠐⠀⢀⠆⠊⣤⠞⠋⠛⠱⡄⠩⢄⠳⣱⢎⡵⣛⣟⡿⠟
⠀⠀⠀⠀⠈⠔⠲⠛⠙⠁⢀⡀⠄⠀⠁⡀⣺⠑⠆⣿⣈⠻⠛⠁⠀⣲⣽⣾⣿⣿⢏⣥⢏⣼⣟⣧⠿⠁⠀⠀⠀⠌⢠⡞⠁⠀⠀⠀⠀⡇⡘⠤⢃⡉⡙⠛⠛⢉⡐⡌
⠀⠀⠀⠀⠀⠀⠑⠂⠒⠈⠂⠐⠠⠀⠀⢠⠐⠧⠂⡷⠉⠒⠀⡀⢄⠛⠿⢛⣋⡴⢛⣵⠾⠿⣽⡚⢠⢀⡤⢶⠀⠀⡟⠲⠀⠀⠀⠂⢡⠇⠀⡉⠀⠁⠱⢪⠤⡃⠘⠈
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢠⣶⡈⢸⠧⠈⠃⢐⣽⣴⣿⣟⣯⣟⣯⣯⣭⣶⠿⠋⢀⠀⠱⣣⢗⡣⡼⢯⡁⢀⠠⠀⠁⠀⠀⠌⡼⠁⢠⢐⡡⠎⡄⠈⢧⡁⢎⡱
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⠟⡙⠇⠀⠇⢠⢶⣛⠞⣻⣿⣾⡿⠿⠛⣋⣡⣦⢶⣿⠆⡀⠐⣯⣛⢶⡻⣽⠀⡀⠀⢂⣀⣄⡤⠞⠁⡘⢄⠲⡐⢣⡘⠁⢆⡱⢊⡵
⠀⠀⠀⠀⠀⠀⠀⠠⠤⢤⣶⣻⣞⠇⠀⢂⢸⡆⠳⣄⣥⠿⠋⣡⣴⣾⣿⣿⡿⠻⢈⠫⡀⠀⢸⢧⣛⡾⣹⢳⠀⠀⠈⠓⠉⠂⠀⡀⢀⠠⠌⢢⠱⡡⠜⡱⡊⡔⠋⠐
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠁⠄⠂⠀⠀⡘⡭⢶⠝⣁⣴⣿⣿⡿⢟⣛⣼⣶⣽⣆⢷⣔⢠⡛⣧⢻⡜⣧⠋⠀⠀⠐⠀⠀⠀⠀⡐⢀⠂⠘⡄⢣⠡⣋⠔⠃⢆⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢄⡴⠁⢃⠉⣄⢿⣿⢋⣥⣶⣿⣿⣿⣿⣿⡟⢘⡵⣫⢲⣭⢳⡽⡎⠁⢀⠂⠀⠀⠀⠀⠂⠄⠂⠈⠄⠸⡁⠆⢐⠂⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠰⠻⣌⠎⢱⣿⣿⣿⣿⣿⡟⢏⣋⡴⣏⠷⣭⢳⣎⠿⡜⠁⠀⠀⠠⠈⡐⠈⠀⠀⠀⠈⠀⠌⠀⠄⡀⠃⠀⠀⠀⠀⢠
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢏⡹⡎⢿⣿⣏⣿⠾⢁⣶⡏⠎⠷⠉⠿⠈⠇⠈⠁⠀⠀⠀⡈⠀⠰⠀⠀⠀⠀⠆⠁⠀⢀⠈⠰⠀⠀⠀⠀⠀⠀⣇
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠻⣽⠲⠜⠬⣖⠽⠋⠀⢀⢀⠠⡀⠀⠂⠀⠀⠀⠀⠀⠐⠠⠈⢀⠐⠀⣲⢌⠠⢈⠐⠀⢈⠀⠀⠀⠀⠀⠀⠘⢤
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠩⣇⣿⣿⠆⣤⠶⠹⠉⠊⠀⠀⠀⠀⠀⠀⠀⠀⡐⢠⣶⠀⠀⡀⢀⣟⢪⠷⡄⠌⠠⠀⠀⠀⠀⠀⠀⠀⡘⠤
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⢻⣿⣜⠃⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣐⡼⣳⡿⠀⢀⠀⡸⠆⠘⢋⡉⠴⣀⣖⣰⠢⡄⢄⠀⠐⠈⣐
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠂⠀⠀⣠⠴⠂⠀⠀⠀⠀⠀⣀⣲⡽⣳⢿⡇⠀⠂⡰⠏⣡⡘⢤⣾⣷⣿⡿⠁⠠⠐⣈⣢⣴⣿⣿
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣀⣤⡠⢄⠀⠀⠀⡠⠔⠋⠀⠀⠀⠀⢠⡔⣀⣡⢾⡱⢯⡽⣿⠂⠁⢀⣡⣾⣵⣿⣿⡿⠟⠿⢻⢿⣿⣿⣿⣿⣿⡻⣿
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣴⡿⣿⣻⡇⠌⢀⠔⠉⠀⠀⠀⠀⠀⣀⠠⠸⣜⡻⣟⢧⡻⢍⢿⠏⠀⢰⣛⠿⠻⠿⠛⣫⣴⣿⣿⣿⣳⡜⢿⣿⣿⣿⡗⡸
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢜⡷⣿⣻⡝⠀⠄⠂⠀⠀⠀⠀⠀⠐⠀⠀⠀⢰⡌⠓⠹⠊⠁⠸⠂⠀⠄⠛⠽⢻⣿⣿⣷⣿⣿⣿⣿⣿⣿⣿⡘⣿⠿⡝⡰⢱
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣠⣿⢻⡽⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⡳⢆⠀⠀⠠⠁⠀⡐⠨⢄⢀⣠⣴⣯⣿⡿⣻⣽⣷⠿⣻⣿⣿⣄⠚⡔⣡⠣
⠀⠀⠀⢀⣤⡴⣞⡶⡆⠀⠀⠀⣰⣟⡇⠹⠀⠀⠀⠀⠀⠀⡀⠂⠀⠀⠀⣠⠴⠀⣠⢿⣍⡏⠂⣀⠦⢠⡴⣶⢮⠄⢸⢧⣟⣿⣿⣿⣶⣌⠘⣰⣿⣿⣿⢿⣆⠜⡠⢓
⠀⢀⣶⣻⢮⠟⠭⢳⠏⡀⠀⢀⡽⡾⠅⠀⠀⠀⠀⣀⡤⠌⠀⠀⠀⠠⢉⡀⢀⡐⣧⠟⠈⠀⠘⣡⠀⣷⡹⣿⣯⠀⠸⣧⢿⣖⣿⣿⣿⣿⣎⢟⣾⣽⣿⣿⣿⣮⠐⡣
⢠⣟⣮⢗⠋⣠⠂⢹⡞⣵⣲⢯⡿⠁⠀⠀⣤⣶⣻⡝⠀⠀⠀⣀⡴⢯⣅⠉⡙⠹⠉⠀⠀⣀⣒⠁⠘⣶⣹⢿⣿⡄⠁⢻⡞⣿⣿⣿⣾⣿⣿⡜⡿⣿⣿⣻⣿⡿⡇⡱
⢼⣫⢞⡽⠚⠁⢠⡾⣽⣳⢯⣏⣗⠀⠰⣟⡷⣏⡷⠈⢀⡤⢲⢤⡒⢦⣍⠓⠀⣀⠤⠐⢡⢏⡼⡀⠈⢧⣏⢿⣻⣷⠈⠠⣟⡳⢯⡽⣹⢮⣟⡽⡈⠳⣻⢿⣿⣟⡇⠐
⠀⠉⠈⣀⣰⣞⣯⡟⣷⣫⠿⣼⡞⡯⢠⢿⣹⠝⠁⠃⣎⡜⡣⠊⠕⠚⠉⠂⠁⠀⢀⡤⢸⣚⡴⣳⠈⠐⣞⢯⡽⣿⣧⠐⠈⡟⣡⣿⣿⣿⣿⣿⣽⡛⣭⣿⣟⠧⠀⠀
⠀⠀⢠⡟⣧⡟⣮⡟⢳⣽⠛⡅⠉⠒⠂⠂⠃⠀⠀⠁⢠⠀⠀⣬⣴⣾⠁⠀⠀⠀⢹⣤⠘⡆⣽⡟⡇⠀⡌⣷⢻⡟⣿⣦⠁⢠⢹⣿⣿⣿⢸⡟⢳⠁⡞⣼⢫⡟⢠⠀
⣀⣄⠾⣽⡹⣞⡇⡼⢯⣳⠤⠐⣠⣾⡛⠁⠀⢀⡄⡀⠀⠀⢁⡂⠝⠂⠀⠀⠀⠁⠰⣯⠀⡇⢸⡿⣽⠄⠐⡽⣚⣿⡿⣿⣂⠀⢸⠛⠿⠛⠀⠋⠁⣰⢳⡹⢞⡂⠌⡐
⡻⠘⣉⢶⡻⡵⠂⠀⠋⢀⣴⡻⣝⠆⠀⠀⠀⠁⠈⡁⠁⠀⣿⡽⡆⠁⠤⡀⠈⠄⠁⣿⠃⡰⢈⡽⣛⢆⠨⡳⣭⢻⣿⣟⣿⡝⣏⠷⣤⣀⣀⡠⢞⡵⣫⠝⠃⠀⡐⠠
⠁⢬⣛⡎⠁⠀⠀⠀⢸⠛⣸⢳⠉⠀⠀⡴⢩⢍⢣⢭⠁⢸⣗⡻⠀⠀⠀⠑⢄⠐⠠⢸⠧⡱⢈⠶⣩⢞⡠⢗⡥⠙⢺⢟⣯⢟⡼⣓⠆⠳⠬⠳⠍⠒⠁⠀⡐⠠⢀⠁
⠈⢲⡍⠀⠀⠀⠀⠀⠀⣸⢧⠃⠀⠀⢸⡐⢣⠎⡎⠖⠀⣾⡹⡇⠀⠀⢤⢲⡠⢳⡀⠈⡳⠅⠸⣍⢻⢿⡰⢫⡜⡂⠘⠎⡜⣎⠶⠁⠀⠂⠀⠄⠀⠄⠂⠁⡀⠂⠄⠂
⢂⠁⡎⠀⠀⠀⠀⠀⢐⣏⠆⠀⠀⠀⠀⠹⣄⠢⣄⠈⠠⣗⢿⠁⠀⣜⢣⡳⢜⡣⠄⢡⠘⡁⠘⠨⠌⠩⠓⠣⠜⠡⠀⠀⠀⠀⠀⠀⠈⠀⠀⠀⢀⠂⢈⠀⠄⡁⠐⠠
⠠⠈⣅⠀⠀⠀⠀⠀⡞⠄⠀⠀⠀⠀⠀⠀⠊⠱⠌⡆⠸⣝⡾⠀⠀⣏⠶⣙⢮⡱⡌⠀⠁⠠⠀⠂⠈⠀⠀⠀⠀⠄⠀⠄⠀⠀⠀⠀⠀⠀⠀⠈⢀⠀⠂⠀⡐⠀⣌⠐
⠀⠀⠈⡉⢀⠀⠀⢀⠋⠀⠀⠀⠀⠀⠀⠀⠀⠀⠁⠀⢸⣏⡞⠀⠀⠊⢁⡴⣣⢷⠩⠆⠠⢀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠀⠐⠀⠀⠁⠀⠈⡀⠄⠂⢁⢰⢧⣛⣧⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
"""


from .config import (
    COLOR_BORDER, COLOR_PROMPT, COLOR_PRIMARY_TEXT, COLOR_TITLE,
    COLOR_SECONDARY_TEXT, COLOR_HIGHLIGHT_FG, COLOR_HIGHLIGHT_BG,
    COLOR_ERROR, COLOR_LOADING_SPINNER, COLOR_ASCII, HEADER_ART
)
from .utils import get_key
from . import config as config_module

class UIManager:
    def __init__(self):
        self.theme = Theme({
            "panel.border": COLOR_BORDER,
            "prompt.prompt": COLOR_PROMPT,
            "prompt.default": COLOR_PRIMARY_TEXT,
            "title": COLOR_TITLE,
            "secondary": COLOR_SECONDARY_TEXT,
            "highlight": f"{COLOR_HIGHLIGHT_FG} on {COLOR_HIGHLIGHT_BG}",
            "error": COLOR_ERROR,
            "info": COLOR_PRIMARY_TEXT,
            "loading": COLOR_LOADING_SPINNER,
        })
        self.console = Console(theme=self.theme)

    def clear(self):
        self.console.clear()

    def print(self, *args, **kwargs):
        self.console.print(*args, **kwargs)

    def get_header_renderable(self) -> Text:
        return Text(HEADER_ART, style=COLOR_ASCII)

    def render_message(self, title: str, message: str, style_name: str):
        self.clear()
        
        # Create styled message text
        message_text = Text()
        for line in message.split('\n'):
            if line.strip():
                message_text.append(line + "\n", style="info" if not line.startswith('•') else "secondary")
            else:
                message_text.append("\n")
        
        panel = Panel(
            Align.center(message_text, vertical="middle"),
            title=Text(title, style="title"),
            box=HEAVY,
            border_style="#FF6B6B" if style_name == "error" else COLOR_BORDER,
            padding=(2, 4),
            width=60
        )
        
        self.console.print(Align.center(panel, vertical="middle", height=self.console.height))
        Prompt.ask(f" {Text('Press ENTER to continue...', style='dim')} ", console=self.console)

    def run_with_loading(self, message: str, target_func, *args):
        self.clear()
        
        result_container = {}
        thread_done = threading.Event()

        def worker():
            try:
                result = target_func(*args)
                result_container['result'] = result
            except Exception as e:
                result_container['error'] = e
            finally:
                thread_done.set()

        loading_thread = threading.Thread(target=worker, daemon=True)
        loading_thread.start()

        spinner = Spinner("dots", text=Text(f" {message}", style=COLOR_LOADING_SPINNER))
        loading_panel = Panel(
            Align.center(spinner, vertical="middle"),
            box=HEAVY,
            border_style=COLOR_BORDER,
            padding=(2, 4),
            title=Text("LOADING", style="title")
        )

        try:
            with Live(Align.center(loading_panel, vertical="middle", height=self.console.height), console=self.console, refresh_per_second=12, screen=True):
                while not thread_done.is_set():
                    time.sleep(0.05)
        except KeyboardInterrupt:
            thread_done.set()
            raise

        self.clear()

        if 'error' in result_container:
            raise result_container['error']
        
        return result_container.get('result')

    def anime_selection_menu(self, results):
        selected = 0
        scroll_offset = 0
        
        screen_height = self.console.height
        target_height = min(screen_height, 35)
        if target_height < 20: target_height = screen_height
        
        vertical_pad = (screen_height - target_height) // 6

        def create_layout():
            layout = Layout(name="root")
            
            if vertical_pad > 0:
                layout.split_column(
                    Layout(size=vertical_pad),
                    Layout(name="content", size=target_height),
                    Layout(size=vertical_pad)
                )
                children = list(layout["root"].children)
                children[0].update(Text(""))
                children[2].update(Text(""))
                content_area = layout["content"]
            else:
                content_area = layout

            content_area.split_column(
                Layout(name="header", size=11),
                Layout(name="body"),
                Layout(name="footer", size=3)
            )
            content_area["body"].split_row(
                Layout(name="left", ratio=1),
                Layout(name="right", ratio=1)
            )
            return layout

        header_renderable = self.get_header_renderable()
        layout = create_layout()
        content_layout = layout["content"] if vertical_pad > 0 else layout

        def generate_renderable():
            content_layout["header"].update(Align.center(header_renderable))
            content_layout["footer"].update(Panel(Text("↑↓ Navigate | ENTER Select | b Back | q Quit", justify="center", style="secondary"), box=HEAVY, border_style=COLOR_BORDER))
            
            max_display = target_height - 11 - 3 - 2
            left_content = Text()
            
            start = scroll_offset
            end = min(start + max_display, len(results))
            
            for idx in range(start, end):
                anime = results[idx]
                is_selected = idx == selected
                
                if is_selected:
                    left_content.append(f"▶ {anime.title_en}\n", style="highlight")
                else:
                    left_content.append(f"  {anime.title_en}\n", style="info")
            
            content_layout["left"].update(Panel(
                left_content,
                title=Text(f"Search Results: {len(results)}", style="title"),
                box=HEAVY,
                border_style=COLOR_BORDER,
                padding=(0, 1)
            ))
            
            selected_anime = results[selected]
            
            container = Table.grid(padding=1)
            container.add_column()
            
            container.add_row(Text(selected_anime.title_en, style="title", justify="center"))
            container.add_row(Text(selected_anime.title_jp, style="secondary", justify="center"))
            
            details_grid = Table.grid(padding=(0, 2), expand=True)
            details_grid.add_column(min_width=25)
            details_grid.add_column()
            
            stats_table = Table.grid(padding=(0, 1), expand=False)
            stats_table.add_column(style="secondary", no_wrap=True, min_width=12)
            stats_table.add_column(style="info", no_wrap=True)
            score_text = "Not found." if selected_anime.score == "0" or selected_anime.score == 0 else f"⭐ {selected_anime.score}/10"
            stats_table.add_row("Score:", Text(score_text, style="#FFA500"))
            stats_table.add_row("Rank:", Text(f"#{selected_anime.rank}", style="title"))
            stats_table.add_row("Popularity:", Text(f"#{selected_anime.popularity}", style="title"))
            stats_table.add_row("Rating:", selected_anime.rating)
            stats_table.add_row("Type:", selected_anime.type)
            stats_table.add_row("Episodes:", selected_anime.episodes)
            stats_table.add_row("Status:", selected_anime.status)
            stats_table.add_row("Aired:", selected_anime.premiered)
            stats_table.add_row("Duration:", f"{selected_anime.duration} min/ep")
            
            text_container = Table.grid()
            text_container.add_column()
            text_container.add_row(Text("Genres", style="title", justify="center"))
            text_container.add_row(Text(selected_anime.genres, style="secondary", justify="center"))
            text_container.add_row("")
            text_container.add_row(Text("Info", style="title", justify="center"))
            text_container.add_row(Text("All anime details loaded instantly!", style="secondary", justify="center"))
            text_container.add_row(Text(f"MAL ID: {selected_anime.mal_id}", style="dim", justify="center"))
            
            details_grid.add_row(Align(stats_table, vertical="top"), text_container)
            container.add_row(details_grid)
            
            content_layout["right"].update(Panel(
                container, 
                title=Text("Details", style="title"),
                box=HEAVY,
                border_style=COLOR_BORDER
            ))
            
            return layout

        self.clear()
        
        with Live(generate_renderable(), console=self.console, auto_refresh=False, screen=True, refresh_per_second=10) as live:
            while True:
                key = get_key()
                max_display = target_height - 11 - 3 - 2
                
                if key == 'UP' and selected > 0:
                    selected -= 1
                    if selected < scroll_offset:
                        scroll_offset = selected
                    live.update(generate_renderable(), refresh=True)
                elif key == 'DOWN' and selected < len(results) - 1:
                    selected += 1
                    if selected >= scroll_offset + max_display:
                        scroll_offset = selected - max_display + 1
                    live.update(generate_renderable(), refresh=True)
                elif key == 'ENTER':
                    return selected
                elif key == 'b':
                    return None
                elif key == 'q' or key == 'ESC':
                    return -1
                
                time.sleep(0.005)

    def episode_selection_menu(self, anime_title, episodes, rpc_manager=None, anime_poster=None, last_watched_ep=None, is_favorite=False, anime_details=None):
        selected = 0
        scroll_offset = 0
        
        if rpc_manager:
            rpc_manager.update_selecting_episode(anime_title, anime_poster)

        screen_height = self.console.height
        target_height = min(screen_height, 35)
        if target_height < 15: target_height = screen_height
        
        vertical_pad = (screen_height - target_height) // 2

        def create_layout():
            layout = Layout(name="root")
            
            if vertical_pad > 0:
                layout.split_column(
                    Layout(size=vertical_pad),
                    Layout(name="content", size=target_height),
                    Layout(size=vertical_pad)
                )
                children = list(layout["root"].children)
                children[0].update(Text(""))
                children[2].update(Text(""))
                content_area = layout["content"]
            else:
                content_area = layout

            content_area.split_column(
                Layout(name="header", size=3),
                Layout(name="body"),
                Layout(name="footer", size=3)
            )
            
            content_area["body"].split_row(
                Layout(name="left", ratio=1),
                Layout(name="right", ratio=6)
            )
            return layout

        layout = create_layout()
        content_layout = layout["content"] if vertical_pad > 0 else layout

        def generate_renderable():
            content_layout["header"].update(Panel(Text(anime_title, justify="center", style="title"), box=HEAVY, border_style=COLOR_BORDER))
            content_layout["footer"].update(Panel(Text("↑↓ Navigate | ENTER Select | g Jump | F Fav | M Batch | b Back", justify="center", style="secondary"), box=HEAVY, border_style=COLOR_BORDER))
            
            max_display = target_height - 3 - 3 - 2
            left_content = Text()
            
            start = scroll_offset
            end = min(start + max_display, len(episodes))
            
            for idx in range(start, end):
                ep = episodes[idx]
                is_selected = idx == selected
                
                type_text = str(ep.type).strip() if ep.type else ""
                if type_text and type_text.lower() != "episode":
                    ep_type_str = f" [{type_text}]"
                else:
                    ep_type_str = ""
                
                # Logic to check if this episode is the last watched
                is_last_watched = False
                if last_watched_ep is not None and str(ep.display_num) == str(last_watched_ep):
                    is_last_watched = True

                # Suffix and style setup
                suffix = ""
                if is_last_watched:
                    suffix = " 👁" # Eye icon to indicate watched
                
                if is_selected:
                    left_content.append(f"▶ {ep.display_num}{ep_type_str}{suffix}\n", style="highlight")
                else:
                    style = "bold green" if is_last_watched else "info"
                    left_content.append(f"  {ep.display_num}{ep_type_str}{suffix}\n", style=style)
            
            content_layout["left"].update(Panel(
                left_content,
                title=Text(f"Episodes: {len(episodes)}", style="title"),
                box=HEAVY,
                border_style=COLOR_BORDER,
                padding=(0, 1)
            ))
            
            # Show anime details in right panel
            fav_icon = "★" if is_favorite else "☆"
            
            if anime_details:
                details_container = Table.grid()
                details_container.add_column()
                
                # Stats table
                stats_table = Table.grid(padding=(0, 1))
                stats_table.add_column(style="secondary", no_wrap=True, min_width=10)
                stats_table.add_column(style="info", no_wrap=True)
                
                score_text = "Not found." if anime_details.get('score') in ["0", 0, None] else f"⭐ {anime_details.get('score', 'N/A')}/10"
                stats_table.add_row("Score:", Text(score_text, style="#FFA500"))
                stats_table.add_row("Rank:", Text(f"#{anime_details.get('rank', 'N/A')}", style="title"))
                stats_table.add_row("Type:", anime_details.get('type', 'N/A'))
                stats_table.add_row("Episodes:", str(anime_details.get('episodes', 'N/A')))
                stats_table.add_row("Status:", anime_details.get('status', 'N/A'))
                if last_watched_ep:
                    stats_table.add_row("Last Watched:", Text(f"Episode {last_watched_ep}", style="bold green"))
                stats_table.add_row("Favorite:", Text(fav_icon + (" Yes" if is_favorite else " No"), style="title"))
                
                details_container.add_row(stats_table)
                details_container.add_row(Text(""))
                details_container.add_row(Text("Genres", style="title", justify="center"))
                details_container.add_row(Text(anime_details.get('genres', 'N/A'), style="secondary", justify="center"))
                
                content_layout["right"].update(Panel(
                    Align.center(details_container, vertical="middle"),
                    title=Text(f"{fav_icon} Info", style="title"),
                    box=HEAVY,
                    border_style=COLOR_BORDER
                ))
            else:
                # Fallback if no anime_details
                selected_ep = episodes[selected]
                right_content = Text(f"Episode {selected_ep.display_num}\n", style="title", justify="center")
                right_content.append("\n")

                if selected_ep.type and str(selected_ep.type).strip().lower() != "episode":
                    right_content.append(f"Type: {selected_ep.type}\n", style="info", justify="center")
                
                if last_watched_ep is not None and str(selected_ep.display_num) == str(last_watched_ep):
                    right_content.append(Text("\n[Last Watched]\n", style="bold green", justify="center"))
                
                right_content.append("\n")
                right_content.append(Text(f"{fav_icon}\n", style="title", justify="center"))
                right_content.append(Text("Favorite: " + ("Yes" if is_favorite else "No"), style="secondary", justify="center"))
                
                content_layout["right"].update(Panel(
                    Align.center(right_content, vertical="middle"),
                    title=Text(f"{fav_icon} Info", style="title"),
                    box=HEAVY,
                    border_style=COLOR_BORDER
                ))
            return layout

        self.clear()

        with Live(generate_renderable(), console=self.console, auto_refresh=False, screen=True, refresh_per_second=10) as live:
            while True:
                key = get_key()
                max_display = target_height - 3 - 3 - 2
                
                if key == 'UP' and selected > 0:
                    selected -= 1
                    if selected < scroll_offset:
                        scroll_offset = selected
                    live.update(generate_renderable(), refresh=True)
                elif key == 'DOWN' and selected < len(episodes) - 1:
                    selected += 1
                    if selected >= scroll_offset + max_display:
                        scroll_offset = selected - max_display + 1
                    live.update(generate_renderable(), refresh=True)
                elif key == 'ENTER':
                    return selected
                elif key == 'f' or key == 'F':
                    return 'toggle_fav'
                elif key == 'm' or key == 'M':
                    return 'batch_mode'
                elif key == 'g':
                    live.stop()
                    try:
                        prompt_panel = Panel(
                            Text("Jump to episode number:", style="info", justify="center"), 
                            box=HEAVY, 
                            border_style=COLOR_BORDER,
                        )

                        self.console.print(Align.center(prompt_panel, vertical="middle", height=7))
                        
                        prompt_string = f" {Text('›', style=COLOR_PROMPT)} "
                        pad_width = (self.console.width - 30) // 2
                        padding = " " * max(0, pad_width)

                        ep_input = Prompt.ask(f"{padding}{prompt_string}", console=self.console)
                        
                        try:
                            ep_num_float = float(ep_input)
                            target_idx = -1
                            for idx, ep in enumerate(episodes):
                                if float(ep.display_num) == ep_num_float:
                                    target_idx = idx
                                    break
                            
                            if target_idx != -1:
                                selected = target_idx
                                scroll_offset = max(0, selected - (max_display // 2))
                            else:
                                self.console.print(Text(f"Episode {ep_input} not found.", style="error"))
                                time.sleep(1)
                        except ValueError:
                            self.console.print(Text("Invalid number.", style="error"))
                            time.sleep(1)

                    except Exception:
                        pass
                    
                    self.clear()
                    live.start()
                    live.update(generate_renderable(), refresh=True)
                
                elif key == 'b':
                    return None
                elif key == 'q' or key == 'ESC':
                    return -1
                
                time.sleep(0.005)

    def batch_selection_menu(self, episodes):
        selected = 0
        scroll_offset = 0
        marked = set()
        
        def generate_renderable():
            content = Text()
            max_display = self.console.height - 10
            visible_episodes = episodes[scroll_offset:scroll_offset + max_display]
            
            for idx, ep in enumerate(visible_episodes):
                real_idx = idx + scroll_offset
                is_selected = real_idx == selected
                is_marked = real_idx in marked
                
                prefix = "▶" if is_selected else " "
                mark = "[x]" if is_marked else "[ ]"
                style = "highlight" if is_selected else "info"
                if is_marked and not is_selected:
                    style = "secondary"
                
                content.append(f"{prefix} {mark} Episode {ep.display_num}\n", style=style)
            
            return Panel(
                Align.center(content, vertical="middle"),
                title=Text(f"Batch Download ({len(marked)} selected)", style="title"),
                box=HEAVY,
                border_style=COLOR_BORDER,
                subtitle=Text("SPACE Toggle | A All | N None | ENTER Download | B Back", style="secondary")
            )

        self.clear()
        
        with Live(Align.center(generate_renderable(), vertical="middle", height=self.console.height), console=self.console, auto_refresh=False, screen=True, refresh_per_second=10) as live:
            while True:
                key = get_key()
                max_display = self.console.height - 10
                
                if key == 'UP' and selected > 0:
                    selected -= 1
                    if selected < scroll_offset:
                        scroll_offset = selected
                    live.update(Align.center(generate_renderable(), vertical="middle", height=self.console.height), refresh=True)
                elif key == 'DOWN' and selected < len(episodes) - 1:
                    selected += 1
                    if selected >= scroll_offset + max_display:
                        scroll_offset = selected - max_display + 1
                    live.update(Align.center(generate_renderable(), vertical="middle", height=self.console.height), refresh=True)
                elif key == ' ':
                    if selected in marked:
                        marked.remove(selected)
                    else:
                        marked.add(selected)
                    live.update(Align.center(generate_renderable(), vertical="middle", height=self.console.height), refresh=True)
                elif key == 'a' or key == 'A':
                    marked = set(range(len(episodes)))
                    live.update(Align.center(generate_renderable(), vertical="middle", height=self.console.height), refresh=True)
                elif key == 'n' or key == 'N':
                    marked.clear()
                    live.update(Align.center(generate_renderable(), vertical="middle", height=self.console.height), refresh=True)
                elif key == 'ENTER':
                    return sorted(list(marked))
                elif key == 'b' or key == 'ESC':
                    return None
                
                time.sleep(0.005)

    def history_menu(self, history_items):
        selected = 0
        scroll_offset = 0
        
        def generate_renderable():
            table = Table(box=None, show_header=False, padding=(0, 1), expand=True)
            table.add_column("Title", style="info")
            table.add_column("Last Ep", style="secondary", justify="right", width=15)
            table.add_column("Date", style="secondary", justify="right", width=20)
            
            max_display = self.console.height - 10
            visible_items = history_items[scroll_offset:scroll_offset + max_display]
            
            for idx, item in enumerate(visible_items):
                real_idx = idx + scroll_offset
                is_selected = real_idx == selected
                
                title = item['title'][:50] + "..." if len(item['title']) > 50 else item['title']
                date_str = item.get('last_updated', '').split('T')[0]
                
                if is_selected:
                    table.add_row(
                        Text(f"▶ {title}", style="highlight"),
                        Text(f"Ep {item.get('episode', '?')}", style="highlight"),
                        Text(date_str, style="highlight")
                    )
                else:
                    table.add_row(
                        f"  {title}",
                        f"Ep {item.get('episode', '?')}",
                        date_str
                    )
            
            return Panel(
                table,
                title=Text(f"Continue Watching ({len(history_items)})", style="title"),
                box=HEAVY,
                border_style=COLOR_BORDER,
                subtitle=Text("ENTER Resume | B Back", style="secondary")
            )

        self.clear()
        
        with Live(Align.center(generate_renderable(), vertical="middle", height=self.console.height), console=self.console, auto_refresh=False, screen=True, refresh_per_second=10) as live:
            while True:
                key = get_key()
                max_display = self.console.height - 10
                
                if key == 'UP' and selected > 0:
                    selected -= 1
                    if selected < scroll_offset:
                        scroll_offset = selected
                    live.update(Align.center(generate_renderable(), vertical="middle", height=self.console.height), refresh=True)
                elif key == 'DOWN' and selected < len(history_items) - 1:
                    selected += 1
                    if selected >= scroll_offset + max_display:
                        scroll_offset = selected - max_display + 1
                    live.update(Align.center(generate_renderable(), vertical="middle", height=self.console.height), refresh=True)
                elif key == 'ENTER':
                    return selected
                elif key == 'b' or key == 'ESC':
                    return None
                
                time.sleep(0.005)

    def favorites_menu(self, fav_items):
        selected = 0
        scroll_offset = 0
        
        def generate_renderable():
            table = Table(box=None, show_header=False, padding=(0, 1), expand=True)
            table.add_column("Title", style="info")
            table.add_column("Added", style="secondary", justify="right", width=20)
            
            max_display = self.console.height - 10
            visible_items = fav_items[scroll_offset:scroll_offset + max_display]
            
            for idx, item in enumerate(visible_items):
                real_idx = idx + scroll_offset
                is_selected = real_idx == selected
                
                title = item['title'][:60] + "..." if len(item['title']) > 60 else item['title']
                date_str = item.get('added_at', '').split('T')[0]
                
                if is_selected:
                    table.add_row(
                        Text(f"▶ {title}", style="highlight"),
                        Text(date_str, style="highlight")
                    )
                else:
                    table.add_row(
                        f"  {title}",
                        date_str
                    )
            
            return Panel(
                table,
                title=Text(f"Favorites ({len(fav_items)})", style="title"),
                box=HEAVY,
                border_style=COLOR_BORDER,
                subtitle=Text("ENTER Watch | R Remove | B Back", style="secondary")
            )

        self.clear()
        
        with Live(Align.center(generate_renderable(), vertical="middle", height=self.console.height), console=self.console, auto_refresh=False, screen=True, refresh_per_second=10) as live:
            while True:
                key = get_key()
                max_display = self.console.height - 10
                
                if key == 'UP' and selected > 0:
                    selected -= 1
                    if selected < scroll_offset:
                        scroll_offset = selected
                    live.update(Align.center(generate_renderable(), vertical="middle", height=self.console.height), refresh=True)
                elif key == 'DOWN' and selected < len(fav_items) - 1:
                    selected += 1
                    if selected >= scroll_offset + max_display:
                        scroll_offset = selected - max_display + 1
                    live.update(Align.center(generate_renderable(), vertical="middle", height=self.console.height), refresh=True)
                elif key == 'ENTER':
                    return (selected, 'watch')
                elif key == 'r' or key == 'R':
                    return (selected, 'remove')
                elif key == 'b' or key == 'ESC':
                    return None
                
                time.sleep(0.005)

    def settings_menu(self, settings_mgr):
        options = [
            ("Default Quality", ["1080p", "720p", "480p"], "default_quality"),
            ("Player", ["mpv", "vlc"], "player"),
            ("Auto Next Episode", [True, False], "auto_next"),
            ("Check Updates", [True, False], "check_updates"),
            ("Theme", ["blue", "red", "green", "purple", "cyan", "yellow", "pink", "orange", "teal", "magenta", "lime", "coral", "lavender", "gold", "mint", "rose"], "theme")
        ]
        selected = 0
        theme_changed = False  # Track if theme was changed
        
        def generate_renderable():
            content = Text()
            
            for idx, (label, choices, key) in enumerate(options):
                current_val = settings_mgr.get(key)
                is_selected = idx == selected
                
                prefix = "▶" if is_selected else " "
                style = "highlight" if is_selected else "info"
                
                val_str = str(current_val)
                if isinstance(current_val, bool):
                    val_str = "Enabled" if current_val else "Disabled"
                
                content.append(f"{prefix} {label}: {val_str}\n", style=style)
            
            return Panel(
                Align.center(content, vertical="middle"),
                title=Text("Settings", style="title"),
                box=HEAVY,
                padding=(2, 4),
                border_style=config_module.COLOR_BORDER,
                subtitle=Text("ENTER Toggle | B Back", style="secondary")
            )

        self.clear()
        
        with Live(Align.center(generate_renderable(), vertical="middle", height=self.console.height), console=self.console, auto_refresh=False, screen=True, refresh_per_second=10) as live:
            while True:
                key = get_key()
                
                if key == 'UP' and selected > 0:
                    selected -= 1
                    live.update(Align.center(generate_renderable(), vertical="middle", height=self.console.height), refresh=True)
                elif key == 'DOWN' and selected < len(options) - 1:
                    selected += 1
                    live.update(Align.center(generate_renderable(), vertical="middle", height=self.console.height), refresh=True)
                elif key == 'ENTER':
                    label, choices, key_name = options[selected]
                    current_val = settings_mgr.get(key_name)
                    
                    # Cycle through choices
                    try:
                        curr_idx = choices.index(current_val)
                        new_val = choices[(curr_idx + 1) % len(choices)]
                    except ValueError:
                        new_val = choices[0]
                        
                    settings_mgr.set(key_name, new_val)
                    
                    # Reload colors if theme changed and apply immediately
                    if key_name == "theme":
                        theme_changed = True  # Mark that theme was changed
                        importlib.reload(config_module)
                        self.theme = Theme({
                            "panel.border": config_module.COLOR_BORDER,
                            "prompt.prompt": config_module.COLOR_PROMPT,
                            "prompt.default": config_module.COLOR_PRIMARY_TEXT,
                            "title": config_module.COLOR_TITLE,
                            "secondary": config_module.COLOR_SECONDARY_TEXT,
                            "highlight": f"{config_module.COLOR_HIGHLIGHT_FG} on {config_module.COLOR_HIGHLIGHT_BG}",
                            "error": config_module.COLOR_ERROR,
                            "info": config_module.COLOR_PRIMARY_TEXT,
                            "loading": config_module.COLOR_LOADING_SPINNER,
                        })
                        self.console = Console(theme=self.theme)
                    
                    live.update(Align.center(generate_renderable(), vertical="middle", height=self.console.height), refresh=True)
                elif key == 'b' or key == 'ESC':
                    # If theme was changed, exit app to apply globally
                    if theme_changed:
                        self.console.clear()
                        self.console.print("\n[bold cyan]Theme changed! Exiting application...[/bold cyan]")
                        self.console.print("[dim]Please run the application again to apply the new theme.[/dim]\n")
                        time.sleep(2)
                        sys.exit(0)
                    return
                
                time.sleep(0.005)

    def quality_selection_menu(self, anime_title, episode_num, available_qualities, rpc_manager=None, anime_poster=None):
        if rpc_manager:
            rpc_manager.update_choosing_quality(anime_title, episode_num, anime_poster)
        
        selected = 0
        
        def generate_renderable():
            content = Text()
            
            for idx, quality in enumerate(available_qualities):
                is_selected = idx == selected
                
                if is_selected:
                    content.append(f"▶ {quality.name}\n", style="highlight")
                else:
                    content.append(f"  {quality.name}\n", style=quality.style)
            
            return Panel(
                content,
                title=Text(f"Episode {episode_num} - Select Quality", style="title"), 
                box=HEAVY,
                padding=(2, 4),
                border_style=COLOR_BORDER,
                subtitle=Text("ENTER Watch | D Download | b Back", style="secondary")
            )

        self.clear()
        
        with Live(Align.center(generate_renderable(), vertical="middle", height=self.console.height), console=self.console, auto_refresh=False, screen=True, refresh_per_second=10) as live:
            while True:
                key = get_key()
                
                if key == 'UP' and selected > 0:
                    selected -= 1
                    live.update(Align.center(generate_renderable(), vertical="middle", height=self.console.height), refresh=True)
                elif key == 'DOWN' and selected < len(available_qualities) - 1:
                    selected += 1
                    live.update(Align.center(generate_renderable(), vertical="middle", height=self.console.height), refresh=True)
                elif key == 'ENTER':
                    return (selected, 'watch')
                elif key == 'd' or key == 'D':
                    return (selected, 'download')
                elif key == 'b':
                    return None
                elif key == 'q' or key == 'ESC':
                    return -1
                
                time.sleep(0.005)

    def post_watch_menu(self):
        options = ["Next Episode", "Previous Episode", "Replay", "Back to List"]
        selected = 0
        
        def generate_renderable():
            content = Text()
            for idx, option in enumerate(options):
                if idx == selected:
                    content.append(f"▶ {option}\n", style="highlight")
                else:
                    content.append(f"  {option}\n", style="info")
            
            return Panel(
                Align.center(content, vertical="middle"),
                title=Text("Finished Watching", style="title"),
                box=HEAVY,
                padding=(1, 4),
                border_style=COLOR_BORDER,
                subtitle=Text("Select Next Action", style="secondary")
            )

        self.clear()
        with Live(Align.center(generate_renderable(), vertical="middle", height=self.console.height), console=self.console, screen=True) as live:
            while True:
                key = get_key()
                if key == 'UP' and selected > 0:
                    selected -= 1
                    live.update(Align.center(generate_renderable(), vertical="middle", height=self.console.height))
                elif key == 'DOWN' and selected < len(options) - 1:
                    selected += 1
                    live.update(Align.center(generate_renderable(), vertical="middle", height=self.console.height))
                elif key == 'ENTER':
                    return options[selected]
                elif key == 'q' or key == 'b' or key == 'ESC':
                    return "Back to List"