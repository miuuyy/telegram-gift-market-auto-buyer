import tkinter as tk
from tkinter import ttk, messagebox
import time
import threading
import pyautogui
from PIL import Image, ImageOps
import pytesseract
import mss
import platform
import re
import os
import json
import sys

# --- Глобальные переменные ---
current_runner = None
stop_event = threading.Event()
is_running = False
DEBUG_OCR = True
DEBUG_OCR_PATH = "ocr_debug_images"
SETTINGS_FILE_NAME = "autoclicker_settings.json"
TESSERACT_BUNDLE_DIR_NAME = "Tesseract-OCR"

initial_warning_shown_this_session = False


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def configure_tesseract():
    global TESSERACT_BUNDLE_DIR_NAME
    tesseract_configured_successfully = False
    tesseract_cmd_to_use = None
    tessdata_prefix_to_use = None
    bundled_tesseract_dir = resource_path(TESSERACT_BUNDLE_DIR_NAME)
    bundled_tesseract_exe = os.path.join(bundled_tesseract_dir, 'tesseract.exe')
    bundled_tessdata_dir = os.path.join(bundled_tesseract_dir, 'tessdata')

    if os.path.isfile(bundled_tesseract_exe) and os.path.isdir(bundled_tessdata_dir):
        tesseract_cmd_to_use = bundled_tesseract_exe
        tessdata_prefix_to_use = bundled_tesseract_dir
        print(f"Tesseract найден в бандле: EXE='{tesseract_cmd_to_use}', TESSDATA_PREFIX='{tessdata_prefix_to_use}'")
        tesseract_configured_successfully = True
    else:
        print(f"Tesseract не найден в ожидаемой бандл-папке: '{bundled_tesseract_dir}'")
        if platform.system() == "Windows":
            standard_tesseract_exe = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
            standard_tessdata_prefix = r'C:\Program Files\Tesseract-OCR'
            standard_tessdata_dir_check = os.path.join(standard_tessdata_prefix, 'tessdata')
            if os.path.isfile(standard_tesseract_exe) and os.path.isdir(standard_tessdata_dir_check):
                tesseract_cmd_to_use = standard_tesseract_exe
                tessdata_prefix_to_use = standard_tessdata_prefix
                print(f"Tesseract найден по стандартному пути: EXE='{tesseract_cmd_to_use}', TESSDATA_PREFIX='{tessdata_prefix_to_use}'")
                tesseract_configured_successfully = True
            else:
                print(f"Tesseract не найден по стандартному пути: '{standard_tesseract_exe}'")

    if tesseract_configured_successfully and tesseract_cmd_to_use and tessdata_prefix_to_use:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd_to_use
        os.environ['TESSDATA_PREFIX'] = tessdata_prefix_to_use
        try:
            version = pytesseract.get_tesseract_version()
            print(f"Tesseract успешно сконфигурирован. Версия: {version}")
            return True
        except Exception as e_verify:
            print(f"Ошибка при проверке конфигурации Tesseract: {e_verify}")
            pytesseract.pytesseract.tesseract_cmd = None
            if 'TESSDATA_PREFIX' in os.environ: del os.environ['TESSDATA_PREFIX']
            return False
    else:
        print("Не удалось сконфигурировать Tesseract.")
        return False

if DEBUG_OCR:
    try:
        actual_debug_ocr_path = resource_path(DEBUG_OCR_PATH)
        if not os.path.exists(actual_debug_ocr_path):
            os.makedirs(actual_debug_ocr_path)
        if not os.access(actual_debug_ocr_path, os.W_OK):
            print(f"Нет прав на запись в папку отладки OCR: '{actual_debug_ocr_path}'")
            DEBUG_OCR = False
    except Exception as e:
        print(f"Не удалось создать/проверить папку для отладки OCR '{DEBUG_OCR_PATH}': {e}")
        DEBUG_OCR = False

def get_mouse_coords(root_window, callback):
    picker_window = tk.Toplevel(root_window)
    picker_window.attributes("-fullscreen", True); picker_window.attributes("-alpha", 0.01)
    picker_window.attributes("-topmost", True); picker_window.config(cursor='crosshair')
    if root_window.winfo_exists(): root_window.withdraw()
    canvas = tk.Canvas(picker_window, highlightthickness=0); canvas.pack(fill="both", expand=True)
    sw, sh = picker_window.winfo_screenwidth(), picker_window.winfo_screenheight()
    canvas.create_text(sw//2, sh//2, text="Click LMB for coordinates\nESC to cancel", fill='red', font=('Arial',20,'bold'), anchor='center', justify='center')
    def on_click(event):
        x,y = event.x_root, event.y_root
        picker_window.destroy()
        if root_window.winfo_exists(): root_window.deiconify()
        callback(x,y)
    def on_escape_event(event):
        picker_window.destroy()
        if root_window.winfo_exists(): root_window.deiconify()
        callback(None,None)
    picker_window.bind("<Button-1>", on_click); picker_window.bind("<Escape>", on_escape_event); picker_window.focus_force()

def select_screen_area(root_window, callback):
    if root_window.winfo_exists(): root_window.withdraw()
    time.sleep(1)
    selector_window = tk.Toplevel(root_window)
    selector_window.attributes("-fullscreen", True); selector_window.attributes("-alpha", 0.3); selector_window.attributes("-topmost", True)
    canvas = tk.Canvas(selector_window, cursor="cross", bg='gray70', highlightthickness=0); canvas.pack(fill="both", expand=True)
    sw, sh = selector_window.winfo_screenwidth(), selector_window.winfo_screenheight()
    canvas.create_text(sw//2, sh//2, text="Select price area with LMB.\nESC to cancel.", fill='white', font=('Arial',20,'bold'), anchor='center', justify='center')
    start_x = start_y = 0; current_rect = None
    def on_mouse_down(event):
        nonlocal start_x, start_y, current_rect
        start_x, start_y = event.x_root, event.y_root
        if current_rect: canvas.delete(current_rect)
        current_rect = canvas.create_rectangle(start_x,start_y,start_x+1,start_y+1,outline='red',width=2)
    def on_mouse_drag(event):
        nonlocal current_rect
        if current_rect: canvas.coords(current_rect, start_x, start_y, event.x_root, event.y_root)
    def on_mouse_up(event):
        nonlocal start_x, start_y
        end_x, end_y = event.x_root, event.y_root
        selector_window.destroy()
        if root_window.winfo_exists(): root_window.deiconify()
        x1,y1 = min(start_x,end_x), min(start_y,end_y)
        w,h = abs(end_x-start_x), abs(end_y-start_y)
        if w > 5 and h > 5: callback(x1,y1,w,h)
        else:
            if root_window.winfo_exists(): messagebox.showwarning("Error","Area too small.",parent=root_window)
            callback(None,None,None,None)
    def on_escape_event_selector(event):
        selector_window.destroy()
        if root_window.winfo_exists(): root_window.deiconify()
        callback(None,None,None,None)
    selector_window.bind("<ButtonPress-1>",on_mouse_down); selector_window.bind("<B1-Motion>",on_mouse_drag)
    selector_window.bind("<ButtonRelease-1>",on_mouse_up); selector_window.bind("<Escape>",on_escape_event_selector); selector_window.focus_force()

def read_text_from_zone(zone_rect):
    if not zone_rect or len(zone_rect) != 4 or any(c is None for c in zone_rect): print("OCR Err: Bad zone"); return None,None
    try:
        import subprocess
        import tempfile
        
        monitor = {"top":int(zone_rect[1]),"left":int(zone_rect[0]),"width":int(zone_rect[2]),"height":int(zone_rect[3])}
        if monitor["width"] <= 0 or monitor["height"] <= 0: print(f"OCR Err: Bad size {monitor}"); return None,None
        with mss.mss() as sct:
            sct_img = sct.grab(monitor)
            img = Image.frombytes("RGB", sct_img.size, sct_img.rgb)
        
        img_processed = img.convert('L')
        
        if DEBUG_OCR:
            try:
                actual_debug_ocr_path = resource_path(DEBUG_OCR_PATH)
                if not os.path.exists(actual_debug_ocr_path): os.makedirs(actual_debug_ocr_path,exist_ok=True)
                ts = time.strftime("%Y%m%d_%H%M%S"); ms = int(time.time()*1000)%1000
                
                # Save RAW COLOR image first to see what we're actually capturing
                fn_raw = f"ocr_debug_RAW_{ts}_{ms:03d}.png"; fp_raw = os.path.join(actual_debug_ocr_path,fn_raw)
                img.save(fp_raw)
                print(f"Saved RAW image: {fp_raw}")
                
                # Save processed grayscale version
                fn = f"ocr_debug_img_{ts}_{ms:03d}.png"; fp = os.path.join(actual_debug_ocr_path,fn)
                img_processed.save(fp)
                print(f"Saved processed image: {fp}")
            except Exception as e_save:
                if not hasattr(read_text_from_zone,'save_error_logged_session'):
                    print(f"OCR Save Err: {e_save} (Path: {fp if 'fp' in locals() else 'N/A'})")
                    read_text_from_zone.save_error_logged_session = True
        
        # Run tesseract directly via subprocess to avoid encoding issues
        try:
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
                img_processed.save(tmp_file.name)
                tmp_path = tmp_file.name
            
            # Find tessdata directory
            tessdata_dir = None
            bundle_tessdata = os.path.join(resource_path(TESSERACT_BUNDLE_DIR_NAME), 'tessdata')
            if os.path.exists(bundle_tessdata):
                tessdata_dir = bundle_tessdata
                print(f"Found tessdata directory: {tessdata_dir}")
            
            # Clear environment to avoid conflicts
            env = os.environ.copy()
            if 'TESSDATA_PREFIX' in env:
                del env['TESSDATA_PREFIX']
                print("Cleared TESSDATA_PREFIX from environment")
            
            # Build command with --tessdata-dir parameter instead of environment variable
            cmd = [
                pytesseract.pytesseract.tesseract_cmd, 
                tmp_path, 
                'stdout',
                '--oem', '3',
                '--psm', '6', 
                '-l', 'eng'
            ]
            
            # Add tessdata-dir if found
            if tessdata_dir:
                cmd.extend(['--tessdata-dir', tessdata_dir])
            
            # Add character whitelist
            cmd.extend(['-c', 'tessedit_char_whitelist=0123456789.,-'])
            
            print(f"Running tesseract command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', env=env)
            raw = result.stdout.strip()
            print(f"Tesseract stdout: '{raw}'")
            if result.stderr.strip():
                print(f"Tesseract stderr: '{result.stderr.strip()}'")
            
            # Clean up temp file
            try:
                os.unlink(tmp_path)
            except:
                pass
                
        except Exception as e:
            print(f"Subprocess tesseract failed: {e}")
            # Fallback to basic pytesseract call
            try:
                raw = pytesseract.image_to_string(img_processed, config='--psm 8').strip()
                print(f"Fallback OCR result: '{raw}'")
            except Exception as e2:
                print(f"Fallback also failed: {e2}")
                raw = ""
        
        print(f"Final OCR result: '{raw}'")
        num = extract_number(raw); return raw, num
    except pytesseract.TesseractNotFoundError: print("OCR CRITICAL: Tesseract not found (runtime)."); return None,None
    except Exception as e: print(f"OCR CRITICAL in read: {type(e).__name__}: {e}"); return None,None

def extract_number(text):
    if not text: return None
    txt = str(text).strip()
    
    # Remove thousand separators (dots and commas) - they represent thousands, not decimals
    # For example: 1.999 means 1999, not 1.999
    txt_clean = txt.replace(',', '').replace('.', '')
    
    # Find all digit sequences
    m = re.search(r'\d+', txt_clean)
    if m:
        s = m.group(0)
        try:
            if not s: return None
            return float(s)
        except ValueError: 
            print(f"Float Err: '{s}' from '{text}' (cleaned: '{txt_clean}')")
            return None
    
    print(f"No digits found in: '{text}' (cleaned: '{txt_clean}')")
    return None

class ClickerRunner(threading.Thread):
    def __init__(self, app_instance):
        super().__init__(daemon=True); self.app=app_instance; self.stop_event=stop_event
    def _perform_single_click(self, coords, type_str, name_str):
        if self.stop_event.is_set(): return False
        if not (isinstance(coords,(list,tuple)) and len(coords)==2 and all(isinstance(c,(int,float))and c>=0 for c in coords)):
            self.app.update_status(f"Skip: Bad coords '{type_str}-{name_str}': {coords}"); return True
        try:
            x,y=int(coords[0]),int(coords[1]); pyautogui.click(x,y)
            self.app.update_status(f"Click {type_str}-{name_str}: ({x},{y})")
            
            # Determine click type for speed multiplier
            click_type = "buy" if type_str == "Cond" else "cycle"
            sleep_time = 0.4 * self.app.get_speed_multiplier(click_type)
            time.sleep(sleep_time)
            return True
        except Exception as e: self.app.update_status(f"Click Err {name_str}({coords}):{e}"); print(f"Click Err:{e}"); return True
    def _perform_ocr_and_conditional_clicks(self, zone, target_num, clicks):
        if self.stop_event.is_set(): return False
        
        # Sleep most of the time FIRST, then do OCR check when price loads at the end
        # OCR loading time uses normal speed (not buy speed)
        sleep_time = 0.65 * self.app.get_speed_multiplier("normal")
        time.sleep(sleep_time)
        
        print(f"\n--- OCR DEBUG: Zone:{zone}, Target:{target_num} ---")
        self.app.update_status(f"OCR Check. Target: ≤{target_num}")
        raw,cur_num = read_text_from_zone(zone)
        print(f"OCR Raw: '{raw}', Num: {cur_num}, Target: {target_num}")
        self.app.update_status(f"OCR:'{raw if raw else "EMPTY"}'➔Num:{cur_num if cur_num is not None else "N/A"}. Target:≤{target_num}")
        met = False
        if cur_num is not None:
            met = cur_num <= target_num
            print(f"OCR Cond: {cur_num} <= {target_num} RESULT: {met}")
        else: print(f"OCR Cond: Num not found. Cond NOT MET.")
        if met:
            msg=f"COND MET: {cur_num}≤{target_num}. Doing {len(clicks)} clicks."; self.app.update_status(msg); print(msg)
            
            # Add extra pause before starting purchase (use buy speed)
            sleep_time = 0.4 * self.app.get_speed_multiplier("buy")
            time.sleep(sleep_time)
            
            for i,c in enumerate(clicks):
                if self.stop_event.is_set(): return False
                if not self._perform_single_click(c,"Cond",f"Click {i+1}"): return False
                
                # Add extra pause between purchase clicks (use buy speed)
                if i < len(clicks) - 1:  # Don't sleep after the last click
                    sleep_time = 0.6 * self.app.get_speed_multiplier("buy")
                    time.sleep(sleep_time)
            
            # Add pause after purchase completion (use buy speed)
            sleep_time = 1.1 * self.app.get_speed_multiplier("buy")
            time.sleep(sleep_time)
            self.app.update_status("Purchase completed, waiting...")
            
        elif cur_num is not None:
            msg=f"COND NOT MET: {cur_num}>{target_num}. Skip clicks."; self.app.update_status(msg); print(msg)
        if not self.stop_event.is_set(): 
            # Final pause uses normal speed
            sleep_time = 0.15 * self.app.get_speed_multiplier("normal")
            time.sleep(sleep_time)
        print(f"--- OCR DEBUG End ---\n"); return True
    def run(self):
        global is_running
        is_running=True; self.stop_event.clear()
        print("[RUNNER] Поток запущен.") 

        zone=self.app.current_zone
        # ИСПОЛЬЗУЕМ ПРАВИЛЬНОЕ ИМЯ АТРИБУТА self.app.target_var (вместо self.app.tv)
        target_s=self.app.target_var.get().strip() 
        cyc_clk=self.app.get_cycle_clicks(); fnd_clk=self.app.get_found_clicks()

        print(f"[RUNNER] Зона: {zone}")
        print(f"[RUNNER] Целевая строка: '{target_s}'")
        print(f"[RUNNER] Циклические клики: {cyc_clk}")
        print(f"[RUNNER] Условные клики: {fnd_clk}")

        if not(zone and len(zone)==4 and all(isinstance(c,(int,float))for c in zone)and zone[2]>0 and zone[3]>0):
            msg = "ERR: Некорректная зона OCR."
            print(f"[RUNNER] ПРОВЕРКА ПРОВАЛЕНА: {msg}")
            self.app.update_status(msg);is_running=False;self.app.on_runner_finish();return
        if not target_s:
            msg = "ERR: Не указано искомое число."
            print(f"[RUNNER] ПРОВЕРКА ПРОВАЛЕНА: {msg}")
            self.app.update_status(msg);is_running=False;self.app.on_runner_finish();return
        try: target_f=float(target_s.replace(',','.'))
        except ValueError:
            msg = f"ERR: Некорректный формат искомого числа '{target_s}'."
            print(f"[RUNNER] ПРОВЕРКА ПРОВАЛЕНА: {msg}")
            self.app.update_status(msg);is_running=False;self.app.on_runner_finish();return
        
        print(f"[RUNNER] Целевое число (float): {target_f}")

        if not(cyc_clk and len(cyc_clk)==4 and all(c and c[0]>=0 and c[1]>=0 for c in cyc_clk)):
            msg = "ERR: Не все 4 циклических клика настроены корректно."
            print(f"[RUNNER] ПРОВЕРКА ПРОВАЛЕНА: {msg}")
            self.app.update_status(msg);is_running=False;self.app.on_runner_finish();return
        if not(fnd_clk and len(fnd_clk)==3 and all(c and c[0]>=0 and c[1]>=0 for c in fnd_clk)):
            msg = "ERR: Не все 3 условных клика настроены корректно."
            print(f"[RUNNER] ПРОВЕРКА ПРОВАЛЕНА: {msg}")
            self.app.update_status(msg);is_running=False;self.app.on_runner_finish();return
        
        print("[RUNNER] Все предварительные проверки пройдены. Начинаю цикл.")
        self.app.update_status("Кликер запущен. Нажмите ESC для остановки."); pyautogui.PAUSE=0.0
        if hasattr(read_text_from_zone,'save_error_logged_session'): del read_text_from_zone.save_error_logged_session
        lc=0
        while not self.stop_event.is_set():
            lc+=1; self.app.update_status(f"Цикл {lc}: Начало...")
            print(f"\n[RUNNER] Начало цикла {lc}. stop_event: {self.stop_event.is_set()}")
            try:
                if platform.system()=="Windows":
                    try:
                        import ctypes
                        if ctypes.windll.user32.GetAsyncKeyState(0x1B)&0x8000: self.app.update_status("ESC Global Stop");self.stop_event.set();break
                    except: pass
                if self.stop_event.is_set():break
                for i in range(2):
                    if not self._perform_single_click(cyc_clk[i],"Cycle",f"Clk {i+1}/4"):self.stop_event.set();break
                if self.stop_event.is_set():break
                if not self._perform_ocr_and_conditional_clicks(zone,target_f,fnd_clk):self.stop_event.set();break
                if self.stop_event.is_set():break
                for i in range(2,4):
                    if not self._perform_single_click(cyc_clk[i],"Cycle",f"Clk {i+1}/4"):self.stop_event.set();break
                if self.stop_event.is_set():break
                if not self._perform_ocr_and_conditional_clicks(zone,target_f,fnd_clk):self.stop_event.set();break
                if self.stop_event.is_set():break
                self.app.update_status(f"Цикл {lc}: Готово.") # Изменено
            except Exception as e: print(f"Loop Err:{e}");self.app.update_status(f"Loop Err:{e}");time.sleep(1)
        is_running=False; self.app.on_runner_finish(); fin_msg="Остановлен." if self.stop_event.is_set() else "Завершен." # Изменено
        self.app.update_status(fin_msg); print(fin_msg)

class AutoClickerApp:
    def on_escape_keypress_main_window(self, event=None): 
        if is_running: 
            self.update_status("ESC в окне - остановка...")
            self.stop_clicker_action() 
            return "break" 

    def __init__(self, root_param):
        self.root = root_param
        self.root.title("Telegram Gift Auto Buyer v3.1") 
        self.root.geometry("900x850"); self.root.resizable(True, True)
        self.root.attributes("-topmost", False)
        
        style = ttk.Style()
        try:
            themes = style.theme_names()
            if 'clam' in themes: style.theme_use('clam')
            elif 'vista' in themes and platform.system() == "Windows": style.theme_use('vista')
        except tk.TclError: print("Не удалось применить тему.")
        
        style.configure("Gray.TLabel", foreground="gray", font=("Arial", 8, "italic"))
        style.configure("TButton", padding=6, font=('Arial', 10))
        style.configure("TLabelframe.Label", font=('Arial', 10, 'bold'))
        
        self.current_zone = None
        self.zone_var = tk.StringVar(value="Price area not selected")
        self.target_var = tk.StringVar()
        self.cycle_clicks_vars = []
        self.found_clicks_vars = []
        self.status_var = tk.StringVar(value="Ready. Configure settings and press START.")
        self.topmost_var = tk.BooleanVar(value=False)
        self.speed_var = tk.IntVar(value=1)  # Speed multiplier: 1=normal, 2=2x faster, etc.


        self.create_interface() 
        self.root.bind('<Escape>', self.on_escape_keypress_main_window) 
        self.root.focus_set()
        self.load_settings()
        self.root.protocol("WM_DELETE_WINDOW", self.on_app_close)

    def on_runner_finish(self):
        if self.root.winfo_exists():
            self.root.after(0, lambda: (self.start_btn.config(state="normal"), self.stop_btn.config(state="disabled")) if self.root.winfo_exists() else None)

    def create_interface(self):
        tp=ttk.Frame(self.root);tp.pack(fill="x",padx=10,pady=(5,0))
        dt="OCR Debug: "
        if DEBUG_OCR:
            try: dt+=f"ON ('{os.path.abspath(resource_path(DEBUG_OCR_PATH))}')"
            except: dt+=f"ON ('{DEBUG_OCR_PATH}' path error)"
        else: dt+="OFF"
        ttk.Label(tp,text=dt,style="Gray.TLabel").pack(side="left")
        
        # Используем self.topmost_var, который был инициализирован в __init__
        speed_frame = ttk.Frame(tp)
        speed_frame.pack(side="right", padx=(0,10))
        ttk.Label(speed_frame, text="Speed:", font=("Arial", 8)).pack(side="left")
        speed_combo = ttk.Combobox(speed_frame, textvariable=self.speed_var, values=[1, 2, 3, 4, 5], width=3, state="readonly")
        speed_combo.pack(side="left", padx=(5,10))
        
        ttk.Checkbutton(tp,text="Always on top",variable=self.topmost_var,command=self.toggle_topmost).pack(side="right")
        ttk.Label(self.root,text="TELEGRAM GIFT AUTO BUYER",font=("Arial",18,"bold")).pack(pady=(5,10))
        mcf=ttk.LabelFrame(self.root,text="Configuration",padding="10"); mcf.pack(fill="both",expand=True,padx=10,pady=5)
        zf=ttk.LabelFrame(mcf,text="1. Price OCR Area",padding="8");zf.pack(fill="x",pady=3)
        # Используем self.zone_var
        ttk.Label(zf,textvariable=self.zone_var).pack(anchor='w')
        ttk.Button(zf,text="Select Price Area",command=self.select_zone_action,width=20).pack(anchor='w',pady=2)
        nf=ttk.LabelFrame(mcf,text="2. Target Price",padding="8");nf.pack(fill="x",pady=3)
        # Используем self.target_var
        ttk.Entry(nf,textvariable=self.target_var,width=15).pack(side="left",padx=(0,5))
        ttk.Label(nf,text="(≤ this price to buy gift)",font=("Arial",8)).pack(side="left")
        caf=ttk.Frame(mcf);caf.pack(fill="x",pady=3)
        # Используем self.cycle_clicks_vars
        cf=ttk.LabelFrame(caf,text="3. Sorting Clicks (4 clicks)",padding="5");cf.pack(side="left",fill="y",expand=True,padx=(0,3))
        sort_labels = ["Sort Menu:", "By Date:", "Sort Menu:", "By Price:"]
        for i in range(4):
            f=ttk.Frame(cf);f.pack(fill="x",pady=1); ttk.Label(f,text=sort_labels[i],width=12).pack(side="left")
            v=tk.StringVar();self.cycle_clicks_vars.append(v); e=ttk.Entry(f,textvariable=v,width=10);e.pack(side="left",padx=2)
            e.bind("<FocusOut>",lambda ev,vv=v:self.validate_coord_entry(vv)); ttk.Button(f,text="🎯",width=2,command=lambda vv=v:self.get_coords_for_var_action(vv)).pack(side="left")
        # Используем self.found_clicks_vars
        ff=ttk.LabelFrame(caf,text="4. Buy Clicks (3 clicks)",padding="5");ff.pack(side="left",fill="y",expand=True,padx=(3,0))
        buy_labels = ["Click Gift:", "Confirm:", "Final Buy:"]
        for i in range(3):
            f=ttk.Frame(ff);f.pack(fill="x",pady=1); ttk.Label(f,text=buy_labels[i],width=10).pack(side="left")
            v=tk.StringVar();self.found_clicks_vars.append(v); e=ttk.Entry(f,textvariable=v,width=10);e.pack(side="left",padx=2)
            e.bind("<FocusOut>",lambda ev,vv=v:self.validate_coord_entry(vv)); ttk.Button(f,text="🎯",width=2,command=lambda vv=v:self.get_coords_for_var_action(vv)).pack(side="left")
        lf=ttk.LabelFrame(mcf,text="How it works",padding="8");lf.pack(fill="x",pady=3)
        lt=("1. Sort Menu → By Date (speed affects all)\n2. Price Check: if price ≤ target → Buy Gift (3 clicks)\n3. Sort Menu → By Price (speed affects all)\n4. Price Check again + Buy if good price\n5. Repeat from step 1 (ESC to stop)\n\nSpeed 1-2: affects everything equally\nSpeed 3+: sorting faster, buying stays normal speed (safe)")
        ttk.Label(lf,text=lt,font=("Arial",8),justify="left").pack(fill='x')
        bf=ttk.Frame(self.root);bf.pack(fill="x",padx=10,pady=5)
        ctf=ttk.LabelFrame(bf,text="Control",padding="8");ctf.pack(side="left",fill="x",expand=True,padx=(0,3))
        bc=ttk.Frame(ctf);bc.pack()
        self.start_btn=ttk.Button(bc,text="🚀 START",command=self.start_clicker,width=12);self.start_btn.pack(side="left",padx=5)
        self.stop_btn=ttk.Button(bc,text="⏹️ STOP",command=self.stop_clicker_action,state="disabled",width=12);self.stop_btn.pack(side="left",padx=5)
        sf=ttk.LabelFrame(bf,text="Status",padding="8");sf.pack(side="left",fill="x",expand=True,padx=(3,0))
        # Используем self.status_var
        ttk.Label(sf,textvariable=self.status_var,wraplength=350,justify="left").pack(fill="x")

    def get_speed_multiplier(self, click_type="normal"):
        """Returns speed multiplier based on click type:
        - For speeds 1-2: all clicks use same multiplier
        - For speeds 3+: sorting clicks use full speed, buy clicks always use speed 1 (normal)
        """
        speed = self.speed_var.get()
        
        if speed <= 2:
            # Speeds 1-2: everything uses same multiplier
            return 1.0 / speed if speed > 0 else 1.0
        else:
            # Speeds 3+: buy clicks always normal speed (1.0), sorting clicks use full speed
            if click_type == "buy":
                return 1.0  # Buy clicks always at normal speed for safety
            else:
                return 1.0 / speed  # Sorting clicks use full speed
    
    def validate_coord_entry(self, sv):
        s=sv.get()
        if not s: return
        try: x,y=map(int,s.split(',')); assert x>=0 and y>=0
        except: sv.set(""); messagebox.showwarning("Coordinates","Invalid format/value: '"+s+"'. Use X,Y (numbers >=0).",parent=self.root)
    def toggle_topmost(self): self.root.attributes("-topmost", self.topmost_var.get()) # Используем self.topmost_var
    def update_status(self, msg):
        if self.root.winfo_exists(): self.root.after(0,lambda:self.status_var.set(msg) if self.root.winfo_exists() else None) # Используем self.status_var

    def select_zone_action(self):
        # Show warning before selection
        messagebox.showinfo("Important", 
                           "YOU MAY SELECT ALL THE PRICE AREA (CONSIDERING BIG NUMBERS) AVOID FAIL BUY", 
                           parent=self.root)
        
        self.update_status("Price area selection mode...")
        def cb(x,y,w,h):
            if x is not None: self.current_zone=(x,y,w,h); self.zone_var.set(f"Area: X{x} Y{y} W{w} H{h}"); self.update_status("Price area selected.") # Используем self.zone_var
            elif not self.current_zone: self.zone_var.set("Price area not selected (cancel/small)"); self.update_status("Price area selection cancelled/small.")
            else: self.update_status("New area selection cancelled. Using previous.")
        select_screen_area(self.root,cb)
    def get_coords_for_var_action(self, vts):
        self.update_status("Coordinate picker mode...")
        get_mouse_coords(self.root,lambda x,y: (vts.set(f"{x},{y}"),self.update_status(f"Coordinates ({x},{y}) set.")) if x is not None else self.update_status("Coordinate selection cancelled."))
    def parse_coords_string(self, s):
        try:
            if s and ',' in s: x,y=map(int,s.split(',')); assert x>=0 and y>=0; return x,y
        except: pass
        return None
    def get_click_coords_from_vars(self, vl, name):
        c=[self.parse_coords_string(v.get()) for v in vl]
        if any(i is None for i in c): messagebox.showerror("Error",f"Not all {name} are configured correctly.",parent=self.root); return None
        return c
    def get_cycle_clicks(self): return self.get_click_coords_from_vars(self.cycle_clicks_vars,"циклические клики") # Используем self.cycle_clicks_vars
    def get_found_clicks(self): return self.get_click_coords_from_vars(self.found_clicks_vars,"дополнительные клики") # Используем self.found_clicks_vars
    def start_clicker(self):
        global current_runner,is_running
        if is_running: messagebox.showwarning("Warning","Already running.",parent=self.root); return
        if hasattr(read_text_from_zone,'save_error_logged_session'): delattr(read_text_from_zone,'save_error_logged_session') 
        self.save_settings()
        current_runner=ClickerRunner(self); current_runner.start()
        self.start_btn.config(state="disabled"); self.stop_btn.config(state="normal")
    def stop_clicker_action(self):
        global stop_event,is_running
        if is_running and current_runner and current_runner.is_alive(): self.update_status("STOP command..."); stop_event.set()
        else: is_running=False; self.on_runner_finish(); self.update_status("Not running / already stopped.")
    def save_settings(self):
        global SETTINGS_FILE_NAME
        s={"zone":self.current_zone,
           "target_number":self.target_var.get(),
           "cycle_clicks":[v.get() for v in self.cycle_clicks_vars],
           "found_clicks":[v.get() for v in self.found_clicks_vars],
           "topmost_on_start":self.topmost_var.get(),
           "speed":self.speed_var.get()}
        try: p=resource_path(SETTINGS_FILE_NAME);open(p,"w").write(json.dumps(s,indent=2))
        except Exception as e: print(f"Ошибка сохранения '{p if 'p' in locals() else SETTINGS_FILE_NAME}': {e}")
    def load_settings(self):
        global SETTINGS_FILE_NAME
        try:
            p=resource_path(SETTINGS_FILE_NAME)
            if not os.path.exists(p): self.update_status("Settings file not found."); return
            s=json.load(open(p,"r"))
            z=s.get("zone")
            if isinstance(z,list)and len(z)==4 and all(isinstance(c,(int,float,type(None)))for c in z):
                if all(c is not None for c in z)and z[2]>0 and z[3]>0: self.current_zone=tuple(z);self.zone_var.set(f"Area: X{z[0]} Y{z[1]} W{z[2]} H{z[3]}")
                else: self.zone_var.set("Price area not selected (file error)")
            self.target_var.set(s.get("target_number",""))
            for i,val in enumerate(s.get("cycle_clicks",[])):
                if i<len(self.cycle_clicks_vars):self.cycle_clicks_vars[i].set(str(val))
            for i,val in enumerate(s.get("found_clicks",[])):
                if i<len(self.found_clicks_vars):self.found_clicks_vars[i].set(str(val))
            self.topmost_var.set(s.get("topmost_on_start",False));self.toggle_topmost()
            self.speed_var.set(s.get("speed", 1))  # Load speed setting, default to 1
            self.update_status("Settings loaded.")
        except Exception as e: print(f"Ошибка загрузки '{p if 'p' in locals() else SETTINGS_FILE_NAME}': {e}")
    def on_app_close(self):
        if is_running:
            if self.root.winfo_exists() and messagebox.askokcancel("Exit","Gift buyer is running. Stop and exit?",parent=self.root):
                self.update_status("Shutting down...");stop_event.set();self.root.after(200,self._check_runner_and_destroy)
        else: self.save_settings(); self.root.destroy() if self.root.winfo_exists() else None
    def _check_runner_and_destroy(self):
        if current_runner and current_runner.is_alive(): self.root.after(100,self._check_runner_and_destroy)
        else: self.save_settings(); self.root.destroy() if self.root.winfo_exists() else None

if __name__ == "__main__":
    root_tk = tk.Tk()
    root_tk.withdraw()
    tesseract_ok = configure_tesseract()
    if not tesseract_ok:
        err_msg=(f"Tesseract OCR configuration error.\nCheck '{TESSERACT_BUNDLE_DIR_NAME}' folder (exe, tessdata, DLLs) "
                 f"next to application, or standard installation 'C:\\Program Files\\Tesseract-OCR'.\nSee console. Exiting.")
        print(err_msg)
        if root_tk.winfo_exists(): messagebox.showerror("Tesseract OCR Error",err_msg,parent=root_tk)
        if root_tk.winfo_exists(): root_tk.destroy()
        sys.exit(1)
    if not initial_warning_shown_this_session:
        tmp_parent = tk.Toplevel(root_tk) if not root_tk.winfo_ismapped() else root_tk
        tmp_parent.withdraw()
        messagebox.showinfo("Important Notice","This script works only in Telegram with android emulator. Be sure you use this tool previously experimented to callibrate best speed avoid fail buying due bad wifi speed.\n"
                            "This message is shown once per session.", parent=tmp_parent)
        initial_warning_shown_this_session = True
        if tmp_parent.winfo_exists() and tmp_parent is not root_tk: tmp_parent.destroy()
    root_tk.deiconify()
    app_instance = AutoClickerApp(root_tk)
    try: root_tk.mainloop()
    except KeyboardInterrupt: print("\nInterrupted (Ctrl+C)."); stop_event.set() if is_running else None
    finally:
        if is_running and current_runner and current_runner.is_alive():
            print("Waiting for thread...");current_runner.join(timeout=1.0)
            if current_runner.is_alive(): print("Thread did not finish in time.")
        print("Program finished.")