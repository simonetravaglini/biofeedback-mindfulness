#Biofeedback mindfulness by Simone TRavaglini
# Licence Apache 2.0
#Da fare: si blocca generazione grafico dopo un po', farlo funzionare anche se non arriva valore HR (modifica sketch arduino), fare grafico HRV, calcolare HR medio di sessione,
#rivedere calcolo HRV se metodo valido, nel grafico mostrare linee senza picchi, 
#

import csv
import random
import serial
import time
import PySimpleGUI as sg
from datetime import datetime
import threading
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import os
import pygame
import matplotlib.ticker as ticker
from scipy.signal import find_peaks
import matplotlib.pyplot as plt
import configparser

#funzione per salvare l'identificativo
def save_identificativo(identificativo):
    config = configparser.ConfigParser()
    config.read('config.ini')
    config['SETTINGS'] = {'identificativo': identificativo}
    with open('config.ini', 'w') as configfile:
        config.write(configfile)

#funzione per caricare l'identificativo
def load_identificativo():
    config = configparser.ConfigParser()
    config.read('config.ini')
    return config.get('SETTINGS', 'identificativo')


#se non ancora creato lo aggiunge al file config.ini
if not os.path.isfile('config.ini'):
    with open('config.ini', 'w') as configfile:
        configfile.write('[SETTINGS]\nidentificativo = \n')

#carico l'identificativo
identificativo = load_identificativo()


# Funzione per ottenere il tempo come intero
def time_as_int():
    return int(round(time.time() * 100))

# Formatta il timer nel formato hh:mm:ss
def format_timer(elapsed_time):
    hours = elapsed_time // 360000
    minutes = (elapsed_time % 360000) // 6000
    seconds = (elapsed_time % 6000) // 100
    return f"{hours:02}:{minutes:02}:{seconds:02}"

# Imposta la sottocartella "AUDIO"
audio_folder = "AUDIO"

# Ottieni la lista dei file audio nella sottocartella "AUDIO"
audio_files = [f for f in os.listdir(audio_folder) if f.endswith(".mp3") or f.endswith(".wav")]

# Inizializza Pygame e imposta il mixer audio
pygame.init()
pygame.mixer.init()

# Definisci lo stato della riproduzione audio
is_playing = False
pause_position = 0  # Posizione di pausa dell'audio

# Inizializza le liste per salvare i dati letti dalla porta seriale
values1 = []
values2 = []
values3 = []
last_values = ['', '', '']  # lista vuota per contenere gli ultimi 3 valori
timestamps = []

# Crea la lista delle porte seriali disponibili
def get_available_ports():
    import serial.tools.list_ports
    ports = list(serial.tools.list_ports.comports())
    return [port.device for port in ports]

# Crea la lista dei baudrate disponibili
baud_list = ['1200', '2400', '4800', '9600', '19200', '38400', '57600', '115200']

# Aggiungi il grafico al layout
layout = [
    [sg.Text('Seleziona la porta seriale:')],
    [sg.Combo(get_available_ports(), size=(30, 1), key='-PORT-', enable_events=True)],
    [sg.Text('Seleziona il baudrate:')],
    [sg.Combo(baud_list, size=(30, 1), key='-BAUD-', default_value='9600')],
    [sg.Button('Connetti', key='-CONNECT-'), sg.Button('Esci', key='-EXIT-')],
    [sg.Column([
        [sg.Text("Inserisci il tuo codice identificativo:"),sg.InputText(identificativo,key='-IDENTIFICATIVO-')],
        [sg.Text("Seleziona un file audio:")],
        [sg.Combo(audio_files, key="-FILE-")],
        [sg.Text('Output seriale:')],
        [sg.Multiline(size=(80, 10), key='-OUTPUT-')],
        [sg.Button('Start', key='-START-'), sg.Button('Stop', key='-STOP-')]
    ]), sg.Column([
        [sg.Text('Ultimi tre valori:')],
        [sg.Text('', size=(80, 1), key='-LAST_VALUES-')],
        [sg.Text('Timer')],
        [sg.Text('', size=(20, 1), key='-TIMER-')],
        [sg.Canvas(key='canvas')]
    ])]
]

# Crea la finestra dell'interfaccia grafica
window = sg.Window('OPENBIOFEEDBACK', layout, finalize=True)

ser = None
reading_serial = False
graph_running = False

# Funzione per l'aggiornamento del grafico
def update_graph():
    fig, ax = plt.subplots()
    line, = ax.plot(timestamps, values3, color='blue', label = 'GSR')
    ax2 = ax.twinx()
    line2, = ax2.plot(timestamps, values1, color='red', label = 'HR')
    line.set_label('GSR')
    line2.set_label('HR')
    ax.legend(loc='upper left')
    ax2.legend(loc='upper right')
    #ax.legend()
    #ax2.legend()

    

    def format_xaxis(x, _):
        return format_timer(int(x))

    #ax.xaxis.set_major_formatter(mdates.FuncFormatter(format_xaxis))
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(format_xaxis))

    canvas = FigureCanvasTkAgg(fig, master=window['canvas'].TKCanvas)
    canvas.draw()
    canvas.get_tk_widget().pack(side='top', fill='both', expand=True)

    while graph_running:
        line.set_data(timestamps, values3)
        line2.set_data(timestamps, values1)
        ax.relim()
        ax.autoscale_view()
        ax2.relim()
        ax2.autoscale_view()

        
        # Imposta solo 5 valori come indicatori sull'asse X
        max_ticks = 5  # Numero di indicatori desiderati sull'asse X
        ax.xaxis.set_major_locator(plt.MaxNLocator(max_ticks))

        
        canvas.draw()
        time.sleep(0.1)

# Thread per l'aggiornamento del grafico
graph_thread = threading.Thread(target=update_graph)

# Loop principale dell'applicazione
while True:
    event, values = window.read()
    if event == '-EXIT-' or event == sg.WIN_CLOSED:
        break
    elif event == '-CONNECT-':
        if not values['-PORT-']:
            sg.popup('Seleziona una porta seriale.')
        else:
            try:
                ser = serial.Serial(values['-PORT-'], int(values['-BAUD-']), timeout=1)
                ser.flushInput()
                sg.popup(f"Connessione riuscita alla porta {values['-PORT-']} con baudrate {values['-BAUD-']}.")
                window.Element('-CONNECT-').Update(disabled=True)
                graph_running = True
                graph_thread.start()
                break
            except Exception as e:
                sg.popup(f"Errore di connessione alla porta seriale: {e}")
                continue

while True:
    event, values = window.read(timeout=100)
    if event == '-EXIT-' or event == sg.WIN_CLOSED:
        break
    elif event == '-START-':
        if not ser:
            sg.popup('Connetti alla porta seriale prima di avviare la lettura.')
        else:
            reading_serial = True
            sg.popup('Lettura iniziata.')
            start_time = time_as_int()
            selected_file = values["-FILE-"]
            identificativo = values["-IDENTIFICATIVO-"]
            save_identificativo(identificativo)

            
            if selected_file:
                file_path = os.path.join(audio_folder, selected_file)
            

                if not is_playing:
                    if pause_position == 0:
                        pygame.mixer.music.load(file_path)
                        pygame.mixer.music.play()
                    else:
                        pygame.mixer.music.play(start=pause_position)

                    is_playing = True
                    window["-STOP-"].update(disabled=False)
                else:
                    sg.popup('Nessun file audio selezionato.')

    elif event == '-STOP-':
        pygame.mixer.music.stop()
        is_playing = False
        window["-STOP-"].update(disabled=True)

        values1.clear()
        values2.clear()
        values3.clear()
        timestamps.clear()

        if reading_serial:
            reading_serial = False
            sg.popup('Lettura interrotta.')
        else:
            sg.popup('La lettura seriale non è in corso.')

    try:
        if reading_serial:
            ser_bytes = ser.readline()
            decoded_bytes = ser_bytes.decode("utf-8").rstrip()
            window['-OUTPUT-'].print(decoded_bytes)

            currentDateAndTime = datetime.now()
            timenow = format_timer(time_as_int() - start_time)
            values = decoded_bytes.split(',')
            values = [v.replace('"', '') for v in values]

            if len(values) == 3:
                try:
                    value1 = float(values[0]) #battiti
                    value2 = float(values[1]) #time
                    value3 = float(values[2]) #gsr

                    values1.append(value1)
                    values2.append(value2)
                    values3.append(value3)
                    timestamps.append(time_as_int() - start_time)

                    #elimino i picchi dall'HRV
                    indici_picchi, _ = find_peaks(values2)
                    valori_senza_picchi = np.delete(values2, indici_picchi)

                    #calcolo lo scarto quadratico medio per HRV
                    sq_diff = np.square(values2 - np.mean(values2))
                    rms = np.sqrt(np.mean(sq_diff))
                    
                    #calcolo lo scarto quadratico medio per HRV senza picchi
                    sq_diff2 = np.square(valori_senza_picchi - np.mean(valori_senza_picchi))
                    rms2 = np.sqrt(np.mean(sq_diff2))

                    
                    # Aggiorna i tre ultimi valori letti
                    last_values.pop(0)
                    last_values.append(f'Time:{value2:.2f}, GSR: {value3:.2f}, Battiti: {value1:.2f}, HRV:{rms:.2f}, HRV senza picchi:{rms2:.2f}')

                    # Aggiorna l'interfaccia grafica con gli ultimi tre valori letti
                    window['-LAST_VALUES-'].update('\n'.join(last_values))

                    # Aggiorna l'interfaccia grafica con il timer
                    window['-TIMER-'].update(timenow)
                    
                except ValueError:
                    continue

    except Exception as e:
        sg.popup(f"Errore di lettura seriale: {e}")
        continue

# Termina il thread del grafico e chiude la porta seriale
graph_running = False
graph_thread.join()

if ser:
    ser.close()

# Chiude la finestra dell'interfaccia grafica
window.close()
