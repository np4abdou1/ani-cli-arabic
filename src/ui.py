import time
import threading
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
        
        layout = Layout()
        layout.split_column(
            Layout(ratio=1),
            Layout(name="message", size=None),
            Layout(ratio=1)
        )
        
        panel = Panel(
            Text(message, justify="center", style="info"),
            title=Text(title, style="title"),
            box=HEAVY,
            border_style=COLOR_BORDER,
            style=f"{style_name}",
            padding=(2, 4)
        )
        
        layout["message"].update(Align.center(panel, vertical="middle"))
        
        self.console.print(Align.center(panel, vertical="middle", height=self.console.height))
        Prompt.ask(f" {Text('Press ENTER to continue...', style='secondary')} ", console=self.console)

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
                    Layout(name="top_pad", size=vertical_pad),
                    Layout(name="content", size=target_height),
                    Layout(name="bottom_pad", size=vertical_pad)
                )
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
            
            details_grid = Table.grid(padding=(0, 1), expand=True)
            details_grid.add_column(ratio=1, no_wrap=True)
            details_grid.add_column(ratio=2)
            
            stats_table = Table.grid(padding=(0, 2))
            stats_table.add_column(style="secondary")
            stats_table.add_column(style="info")
            stats_table.add_row("Score:", Text(f"{selected_anime.score}/10", style="title"))
            stats_table.add_row("Rank:", Text(f"#{selected_anime.rank}", style="title"))
            stats_table.add_row("Popularity:", Text(f"#{selected_anime.popularity}", style="title"))
            stats_table.add_row("Rating:", selected_anime.rating)
            stats_table.add_row("Type:", selected_anime.type)
            stats_table.add_row("Episodes:", selected_anime.episodes)
            stats_table.add_row("Status:", selected_anime.status)
            stats_table.add_row("Aired:", selected_anime.premiered)
            stats_table.add_row("Studio:", selected_anime.creators)
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

    def episode_selection_menu(self, anime_title, episodes, rpc_manager=None, anime_poster=None, last_watched_ep=None):
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
                    Layout(name="top_pad", size=vertical_pad),
                    Layout(name="content", size=target_height),
                    Layout(name="bottom_pad", size=vertical_pad)
                )
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
            # Updated Footer with L key
            content_layout["footer"].update(Panel(Text("↑↓ Navigate | ENTER Select | g Jump | l Last | b Back", justify="center", style="secondary"), box=HEAVY, border_style=COLOR_BORDER))
            
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
            
            selected_ep = episodes[selected]
            right_content = Text(EPISODE_ASCII_ART, style=COLOR_ASCII, justify="center")
            right_content.append("\n")
            right_content.append(Text(f"Episode {selected_ep.display_num}\n", style="title", justify="center"))

            if selected_ep.type and str(selected_ep.type).strip().lower() != "episode":
                right_content.append(f"Type: {selected_ep.type}\n", style="info")
            
            if last_watched_ep is not None and str(selected_ep.display_num) == str(last_watched_ep):
                right_content.append(Text("\n[Last Watched]\n", style="bold green", justify="center"))

            right_content.append("\n")
            right_content.append(Text.from_markup("Press [highlight]ENTER[/highlight] to select.", justify="center"))
            right_content.append("\n")
            right_content.append(Text.from_markup("Press [highlight]G[/highlight] to jump.", justify="center"))
            right_content.append("\n")
            right_content.append(Text.from_markup("Press [highlight]L[/highlight] to go to last watched.", justify="center"))
            
            content_layout["right"].update(Panel(
                Align.center(right_content, vertical="middle"),
                title=Text("<3", style="title"),
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
                
                # --- NEW LOGIC FOR L KEY ---
                elif key == 'l':
                    if last_watched_ep is not None:
                        target_idx = -1
                        for idx, ep in enumerate(episodes):
                            if str(ep.display_num) == str(last_watched_ep):
                                target_idx = idx
                                break
                        
                        if target_idx != -1:
                            selected = target_idx
                            scroll_offset = max(0, selected - (max_display // 2))
                            live.update(generate_renderable(), refresh=True)
                        else:
                            # If episode not found in list despite being in history
                            pass
                    else:
                        # Optional: flash a message that no history exists
                        pass
                # ---------------------------
                
                elif key == 'b':
                    return None
                elif key == 'q' or key == 'ESC':
                    return -1
                
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
                Align.center(content, vertical="middle"),
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