import requests
import networkx as nx
import matplotlib.pyplot as plt
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, font
from PIL import Image, ImageTk



# LOGICA BGP STATE
def get_historical_data(ip, timestamp):
    url = f'https://stat.ripe.net/data/bgp-state/data.json?resource={ip}&timestamp={timestamp}'
    response = requests.get(url)
    return response.json() # Regresa un diccionario con la información obtenida del JSON

def process_data(data, ip):
    if 'data' in data and 'bgp_state' in data['data']:
        events = data['data']['bgp_state']
        print(f"Total eventos: {len(events)}")  # Imprimir el número total de eventos
        announcements = [event for event in events if event['target_prefix'] == ip]
        print(f"Total anuncios: {len(announcements)}")  # Imprimir el número total de anuncios
        return announcements
    else:
        print("No events found in the data.")
        return [], []

def build_graph(announcements):
    G = nx.DiGraph()  # Use a directed graph
    for event in announcements:
        path = event['path']
        for i in range(len(path) - 1):
            G.add_edge(path[i], path[i + 1])
    return G

def plot_graph(G):
    plt.figure(figsize=(12, 8))
    pos = nx.spring_layout(G, k=0.1, iterations=100)  # Ajustar el layout para mejor separación
    nx.draw(G, pos, with_labels=True, node_size=350, node_color="skyblue", font_size=6, font_weight="bold", edge_color="gray", width=1.5, alpha=0.7, arrows=False)
    plt.title('Grafico de Anuncios de Prefijos')
    plt.show()

# LOGICA BGP PLAY
def graficar(lista_as_paths, fecha):
    as_origen = lista_as_paths[0][-1]

    G = nx.DiGraph()

    for path in lista_as_paths:
        edges = [(path[i], path[i+1]) for i in range(len(path) - 1)]
        G.add_edges_from(edges)
    
    pos = nx.spring_layout(G)
    pos[as_origen] = [0, 0]

    for nodo in pos:
        if nodo != as_origen:
            pos[nodo] = pos[nodo] * 1.5  # Vamos escalando a partir del origen

    
    plt.figure(figsize=(12, 8)) # Tamaño de la figura
    #plt.text(0.5, 1.05, "-", horizontalalignment='center', verticalalignment='center', 
             #fontsize=12, bbox=dict(facecolor='white', edgecolor='black', boxstyle='round,pad=0.5'))
    plt.title(f'{fecha}')
    pos = nx.spring_layout(G)  # Mejor visualizacion
    nx.draw(G, pos, with_labels=True, node_size=100, node_color='lightblue', font_size=10, font_weight='bold', arrows=False)
    nx.draw_networkx_nodes(G, pos, nodelist=[as_origen], node_color='red', node_size=1000)  # Highlight the origin AS 
    plt.show()

def GET_API(ip_publica, fecha_inicio, fecha_final):
    url = f'https://stat.ripe.net/data/bgplay/data.json?resource={ip_publica}&starttime={fecha_inicio}&endtime={fecha_final}'
    response = requests.get(url) # Metodo GET 
    return response.json() # Regresa un diccionario con la información obtenida del JSON

def automatizado(data, ASN_objetivo):

    lista_as_paths_filtrada = []
    for state in data['data']['initial_state']:
        path = state['path']
        if ASN_objetivo in path:
            # Find the index of the target ASN
            index = path.index(ASN_objetivo)
            # Slice the path to start from the target ASN
            trimmed_path = path[index:]
            lista_as_paths_filtrada.append(trimmed_path)
            
    cleaned_paths = []
    for path in lista_as_paths_filtrada:
        # Remove duplicate occurrences of the target ASN (1299)
        seen = False
        cleaned_path = []
        for asn in path:
            if asn == ASN_objetivo:
                if not seen:
                    cleaned_path.append(asn)
                    seen = True
            else:
                cleaned_path.append(asn)
        cleaned_paths.append(cleaned_path)

    unique_paths = set(tuple(path) for path in cleaned_paths)
    lista_as_paths = [list(path) for path in unique_paths]
    
    return lista_as_paths
    
def arreglo(data, asn, ip, original, end_date):
    global local_cont
    
    events = data['data']['events']
    # sacamos los withdrawals de la ecuacion
    paths = [
        event['timestamp']
        for event in events
        if 'path' in event['attrs'] and event['attrs']['path'][0] == asn
    ]
    
    lenght_iter = len(paths)
    if (local_cont>lenght_iter):
        local_cont = 0
    
    if (len(paths) != 0):
        timestamp = paths[local_cont]
        print(timestamp)
        diccio = GET_API(ip, timestamp, end_date)
        updated_paths = automatizado(diccio, asn)
        return updated_paths, timestamp
    elif (len(paths) == 0):
        diccio = GET_API(ip, original, end_date)
        updated_paths = automatizado(diccio, asn)
        return updated_paths, original
        
def cont(ip, asn, start_date, end_date, mensaje):
    global local_cont, initial_paths
    local_cont = local_cont + mensaje
    
    original = start_date
    diccionario = GET_API(ip, original, end_date)
    initial_paths = automatizado(diccionario, asn)
    
    if (local_cont <= -1):
        local_cont = -1
        lista_actual = automatizado(diccionario, asn)
        fecha = original
    else:
        lista_actual, fecha = arreglo(diccionario, asn, ip, original, end_date)
    
    print(lista_actual)
    graficar(lista_actual, fecha)
    

def vamonos(ip, asn, start_date, end_date):
    global local_cont
    V = tk.Toplevel()
    V.geometry('400x200')
    V.grid_columnconfigure(0, weight=1)  # Make the first column expandable
    V.grid_columnconfigure(1, weight=1)
    V.grid_rowconfigure(0, weight=1)
    #V.config(bg='DarkOrchid4')
    #newlabel=tk.Label(V, text='Gráficas', font=('Helvetica', 20), bg='gold')
    #newlabel.pack()

    botonv1=tk.Button(V, text='←',bg='white', command=lambda m=-1: cont(ip, asn, start_date, end_date, m))
    botonv1.grid(row=0, column=0, sticky="nsew")
    botonv2=tk.Button(V, text='→',bg='white', command=lambda m=1: cont(ip, asn, start_date, end_date, m))
    botonv2.grid(row=0, column=1, sticky="nsew")
    

############################
# Animacion del GIF
class AnimatedGIF(tk.Label):
    def __init__(self, parent, gif_path, delay=200, **kwargs):
        tk.Label.__init__(self, parent, **kwargs)
        self.gif_path = gif_path
        self.delay = delay  # Delay en ms
        self.frames = []
        self.load_frames()
        self.current_frame = 0
        if self.frames:
            self.config(image=self.frames[0])
            self.after(0, self.update_animation)
        else:
            print("No frames found for the GIF.")

    def load_frames(self):
        try:
            with Image.open(self.gif_path) as img:
                for i in range(img.n_frames):
                    img.seek(i)
                    frame = img.copy().convert('RGBA')
                    
                    # Crear una imagen nueva con fondo transparente
                    transparent_frame = Image.new('RGBA', frame.size, (0, 0, 0, 0))
                    
                    # Pegar el frame al fondo, usando el frame como mascara
                    transparent_frame.paste(frame, (0, 0), frame)
                    
                    # Convertir a PhotoImage
                    photo_frame = ImageTk.PhotoImage(transparent_frame)
                    
                    self.frames.append(photo_frame)
                print(f"Loaded {len(self.frames)} frames.")
        except Exception as e:
            print(f"Error con el GIF: {e}")

    def update_animation(self):
        if self.frames:
            self.config(image=self.frames[self.current_frame])
            self.current_frame = (self.current_frame + 1) % len(self.frames)
            self.after(self.delay, self.update_animation)
        else:
            print("No hay frames en el GIF.")
##########################

def blink_button():
    current_style = style.lookup("BlinkingButton.TButton", "foreground")
    new_color = '#FFFFFF' if current_style == '#FF00FF' else '#FF00FF'
    style.configure("BlinkingButton.TButton", foreground=new_color)
    root.after(400, blink_button)

def on_submit():
    valid = True
    ip = "190.14.11.0/24"
    #ip = "8.8.8.0/24"
    ip = ip_entry.get()
    #asn = 1299
    #asn = 62167
    #asn = 35598
    asn = int(asn_entry.get())
    #start_date = "2024-08-02T19:00:00"
    start_date = start_date_entry.get()
    #end_date = "2024-08-03T23:00:00"
    end_date = end_date_entry.get()
    bgp = check_var.get()
    
#     if not ip or not asn or not start_date or not end_date:
#         messagebox.showerror("Error", "Todos los campos son requeridos.")
#         valid = False
#     try:
#         datetime.strptime(start_date, '%Y-%m-%dT%H:%M:%S')
#         datetime.strptime(end_date, '%Y-%m-%dT%H:%M:%S')
#     except ValueError:
#         messagebox.showerror("Error", "El formato de fecha debe ser: YYYY-MM-DDTHH:MM:SS")
#         #V.destroy()
#         valid = False
#         
#     if (valid):
#         vamonos(ip, asn, start_date, end_date)
#     else:
#         pass
    if (bgp):
        vamonos(ip, asn, start_date, end_date)
    else:
        data = get_historical_data(ip, start_date)
        announcements = process_data(data, ip)   
        
        if announcements:
            G = build_graph(announcements)
            plot_graph(G)
        else:
            messagebox.showerror("No hay datos")
    
# GUI setup
root = tk.Tk()
root.title("BGPplay Data Analyzer")
root.configure(bg="#000080")  # color del fondo

window_width = 800  # Dimensiones de la ventana
window_height = 750  
local_cont = -1
# Que aparezca en el centro la ventana
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()
x = (screen_width - window_width) // 2
y = (screen_height - window_height) // 2

root.geometry(f"{window_width}x{window_height}+{x}+{y}")

# Fonts
label_font = font.Font(family="Courier", size=12, weight="bold")
entry_font = font.Font(family="Courier", size=16, weight="bold")  # Larger font for entry fields
title_font = font.Font(family="Courier", size=24, weight="bold")  # Larger font for title

# Crear objetos de estilo y customizarlos
style = ttk.Style()
style.theme_use('default')
style.configure("TFrame", background="#000080")
style.configure("TLabel", background="#000080", foreground="#00FFFF", font=label_font, anchor="center")
style.configure("TEntry", fieldbackground="#000000", foreground="#00FF00", font=entry_font, justify="center")
style.configure("BlinkingButton.TButton", background="#FF00FF", foreground="#FFFFFF", font=label_font)

# crear el marco/fondo
mainframe = ttk.Frame(root, padding="20", style="TFrame")
mainframe.place(relx=0.5, rely=0.5, anchor="center")

# Crear la matriz y widgets
title_label = ttk.Label(mainframe, text="BGPplay Data Analyzer", font=title_font, foreground="#FFFF00")
title_label.grid(row=0, column=0, columnspan=2, pady=20)

labels = ["Prefijo IP:", "ASN:", "Fecha de inicio:", "Fecha final:"]
entries = [ip_entry, asn_entry, start_date_entry, end_date_entry] = [ttk.Entry(mainframe, width=25, style="TEntry") for _ in range(4)]

for i, (label_text, entry) in enumerate(zip(labels, entries), start=1):
    ttk.Label(mainframe, text=label_text).grid(row=i, column=0, sticky=tk.W, padx=10, pady=10)
    entry.grid(row=i, column=1, padx=10, pady=10)

submit_button = ttk.Button(mainframe, text="¡GO!", command=on_submit, style="BlinkingButton.TButton")
submit_button.grid(row=5, column=0, columnspan=2, pady=20)

check_var = tk.BooleanVar(value=False)
toggle_button = ttk.Checkbutton(root, text="BGP Play", variable = check_var)
toggle_button.grid(row=1, column=0, columnspan=2, pady=20)

# Linea rosa
canvas = tk.Canvas(mainframe, width=300, height=3, bg="#000080", highlightthickness=0)
canvas.grid(row=6, column=0, columnspan=2, pady=10)
canvas.create_line(0, 1, 300, 1, fill="#FF00FF", width=2)

# GIF
# CAMBIAR PATH DE SER NECESARIO
gif_path = r"C:\CJ\2024\II CICLO\Telecomunicaciones 1\sonic1.gif"
animated_gif = AnimatedGIF(mainframe, gif_path, delay=20, bg="#000080")
animated_gif.grid(row=7, column=0, columnspan=2, pady=10)

# texto final
status_label = ttk.Label(mainframe, text="SYSTEM READY", foreground="#00FF00", font=("Courier", 14, "bold"))
status_label.grid(row=8, column=0, columnspan=2, pady=10)

# Efecto de parpadeo
blink_button()

# Centrar el marco
root.grid_rowconfigure(0, weight=1)
root.grid_columnconfigure(0, weight=1)

root.mainloop()