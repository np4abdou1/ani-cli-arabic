import os
import sys

if os.name == 'nt':
    import msvcrt
else:
    import tty
    import termios
    import select

def is_bundled():
    return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')

def get_key():
    if os.name == 'nt':
        if msvcrt.kbhit():
            key = msvcrt.getch()
            if key == b'\xe0' or key == b'\x00':
                key2 = msvcrt.getch()
                if key2 == b'H': return 'UP'
                elif key2 == b'P': return 'DOWN'
                elif key2 == b'M': return 'RIGHT'
                elif key2 == b'K': return 'LEFT'
            elif key == b'\r': return 'ENTER'
            elif key == b'\x1b': return 'ESC'
            elif key == b'q' or key == b'Q': return 'q'
            elif key == b'g' or key == b'G': return 'g'
            elif key == b'b' or key == b'B': return 'b'
            elif key == b'/' or key == b'?': return '/'
            else: return key.decode('utf-8', errors='ignore')
        return None
    else:
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            if select.select([sys.stdin], [], [], 0.01)[0]:
                ch = sys.stdin.read(1)
                if ch == '\x1b':
                    ch2 = sys.stdin.read(1)
                    if ch2 == '[':
                        ch3 = sys.stdin.read(1)
                        if ch3 == 'A': return 'UP'
                        elif ch3 == 'B': return 'DOWN'
                        elif ch3 == 'C': return 'RIGHT'
                        elif ch3 == 'D': return 'LEFT'
                    return 'ESC'
                elif ch == '\r' or ch == '\n': return 'ENTER'
                elif ch == 'q' or ch == 'Q': return 'q'
                elif ch == 'g' or ch == 'G': return 'g'
                elif ch == 'b' or ch == 'B': return 'b'
                elif ch == '/' or ch == '?': return '/'
                return ch
            return None
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
