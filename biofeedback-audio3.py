#Biofeedback mindfulness by Simone TRavaglini
# Licence Apache 2.0
#Da fare:  farlo funzionare anche se non arriva valore HR (modifica sketch arduino), 
#PROBLEMI: quando riparte il grafico viene ricreato un nuovo grafico invece che aggiornato il precedente, rimettere creazione CSV
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
from hrvanalysis import remove_outliers, remove_ectopic_beats, interpolate_nan_values
from hrvanalysis import get_time_domain_features



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
interpolati = []
battiti = []

# Crea la lista delle porte seriali disponibili
def get_available_ports():
    import serial.tools.list_ports
    ports = list(serial.tools.list_ports.comports())
    return [port.device for port in ports]

# Crea la lista dei baudrate disponibili
baud_list = ['1200', '2400', '4800', '9600', '19200', '38400', '57600', '115200']

# Definisci il layout
layout = [
    [
        sg.Column([
            [sg.Text('Seleziona la porta seriale:')],
            [sg.Combo(get_available_ports(), size=(30, 1), key='-PORT-', enable_events=True)],
            [sg.Text('Seleziona il baudrate:')],
            [sg.Combo(baud_list, size=(30, 1), key='-BAUD-', default_value='9600')],
            [sg.Button('Connetti', key='-CONNECT-'), sg.Button('Esci', key='-EXIT-')]
        ], vertical_alignment='top'),
    
    
        sg.Column([
            [sg.Text("Inserisci il tuo codice identificativo:"), sg.InputText(identificativo, key='-IDENTIFICATIVO-')],
            [sg.Text("Seleziona un file audio:")],
            [sg.Combo(audio_files, key="-FILE-")],
            [sg.Text('Output seriale:')],
            [sg.Multiline(size=(50, 10), key='-OUTPUT-')],
            [sg.Button('Start', key='-START-'), sg.Button('Stop', key='-STOP-')],
            [sg.Text('Ultimi tre valori:')],
            [sg.Text('', size=(50, 3), key='-LAST_VALUES-')],
            [sg.Text('Timer')],
            [sg.Text('', size=(50, 1), key='-TIMER-')],
        ], vertical_alignment='top'),
        
        sg.Column([
            [sg.Canvas(key='canvas')]
        ], vertical_alignment='top'),

        sg.Column([
            [sg.Canvas(key='canvas2')]
        ], vertical_alignment='top')
    ]
]


# Crea la finestra dell'interfaccia grafica
window = sg.Window('OPENBIOFEEDBACK', layout, finalize=True,resizable=True)

#inizializza variabili a FALSE
ser = None
reading_serial = False
graph_running = False




def create_graph():
      
        fig, ax = plt.subplots()
        fig2, ax2 = plt.subplots()
        line, = ax.plot(timestamps, values3, color='blue', label = 'GSR')
        line2, = ax2.plot(timestamps, values1, color='red', label = 'HR')
        line2b, = ax2.plot(timestamps, battiti, color='black', label = 'TIME')
        line.set_label('GSR')
        line2.set_label('HR')
        ax.legend(loc='upper right')
        ax2.legend(loc='upper right')
        #ax.legend()
        #ax2.legend()
        
        def format_xaxis(x, _):
            return format_timer(int(x))

        #formatto asse X hh:mm:ss
        ax.xaxis.set_major_formatter(ticker.FuncFormatter(format_xaxis))
        ax2.xaxis.set_major_formatter(ticker.FuncFormatter(format_xaxis))  

        canvas = FigureCanvasTkAgg(fig, master=window['canvas'].TKCanvas)
        canvas.draw()
        canvas.get_tk_widget().pack(side='top', fill='both', expand=True)

        canvas2 = FigureCanvasTkAgg(fig2, master=window['canvas2'].TKCanvas)
        canvas2.draw()
        canvas2.get_tk_widget().pack(side='top', fill='both', expand=True)
       
    
        canvas.draw()
        canvas2.draw()
       
        time.sleep(0.1)
#fine funzione aggiornamento grafico




# Funzione per l'aggiornamento del grafico
def update_graph():
          
        fig, ax = plt.subplots()
        fig2, ax2 = plt.subplots()
        line, = ax.plot(timestamps, values3, color='blue', label = 'GSR')
        line2, = ax2.plot(timestamps, values1, color='red', label = 'HR')
        line2b, = ax2.plot(timestamps, battiti, color='black', label = 'TIME')
        line.set_label('GSR')
        line2.set_label('HR')
        ax.legend(loc='upper right')
        ax2.legend(loc='upper right')
        #ax.legend()
        #ax2.legend()
        
        def format_xaxis(x, _):
            return format_timer(int(x))

        #formatto asse X hh:mm:ss
        ax.xaxis.set_major_formatter(ticker.FuncFormatter(format_xaxis))
        ax2.xaxis.set_major_formatter(ticker.FuncFormatter(format_xaxis))  

        canvas = FigureCanvasTkAgg(fig, master=window['canvas'].TKCanvas)
        canvas.draw()
        canvas.get_tk_widget().pack(side='top', fill='both', expand=True)

        canvas2 = FigureCanvasTkAgg(fig2, master=window['canvas2'].TKCanvas)
        canvas2.draw()
        canvas2.get_tk_widget().pack(side='top', fill='both', expand=True)


        while graph_running:
            line.set_data(timestamps, values3)
            line2.set_data(timestamps, values1)
            line2b.set_data(timestamps, battiti)
            ax.relim()
            ax.autoscale_view()
            ax2.relim()
            ax2.autoscale_view()
            
            # Imposta solo 5 valori come indicatori sull'asse X
            max_ticks = 5  # Numero di indicatori desiderati sull'asse X
            ax.xaxis.set_major_locator(plt.MaxNLocator(max_ticks))
            ax2.xaxis.set_major_locator(plt.MaxNLocator(max_ticks))
        
            canvas.draw()
            canvas2.draw()
            print("graph is running")
            time.sleep(0.1)
#fine funzione aggiornamento grafico


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
            window["-STOP-"].update(disabled=False)
            
            reading_serial = True
            #fai partire i grafici
                       
            graph_running = True
            graph_thread = threading.Thread(target=update_graph)
            graph_thread.start()
            #firstRun = False
            
            sg.popup('Lettura iniziata.')
            # Cancella tutti i valori precedenti accumulati nella coda seriale - NON FUNZIONA
            ser.flush()
            #ser.flushInput()
            
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
        graph_running = False        
        is_playing = False
        window["-STOP-"].update(disabled=True)
        
        #svuoto tutte le serie di dati acquisite
        values1.clear()
        values2.clear()
        values3.clear()
        rr_intervals_without_outliers.clear()
        timestamps.clear()
        interpolati.clear()
        battiti.clear()
        
        # Aggiorna l'interfaccia grafica con i valori resettati
        window['-LAST_VALUES-'].update('')
        window['-TIMER-'].update('')


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
                    rr_intervals_without_outliers = remove_outliers(rr_intervals=values2,  
                                                low_rri=300, high_rri=2000)
                    interpolated_rr_intervals = interpolate_nan_values(rr_intervals=rr_intervals_without_outliers,
                                                   interpolation_method="linear")
                    # This remove ectopic beats from signal
                    nn_intervals_list = remove_ectopic_beats(rr_intervals=interpolated_rr_intervals, method="malik")
                    # This replace ectopic beats nan values with linear interpolation
                    interpolated_nn_intervals = interpolate_nan_values(rr_intervals=nn_intervals_list)
                    interpolati = interpolated_nn_intervals
                    battiti = [60000 / x  for x in interpolati] #calcolo battiti ripuliti

                    time_domain_features = get_time_domain_features(interpolated_nn_intervals)
                    min_hr = time_domain_features['min_hr']
                    max_hr = time_domain_features['max_hr']
                    mean_hr = time_domain_features['mean_hr']
                    mean_nni = time_domain_features['mean_nni']
                    sd_nn = time_domain_features['sdnn']
                    rmssd = time_domain_features['rmssd']

                    #>>> time_domain_features
                    #{'mean_nni': 718.248,
                    #'sdnn': 43.113,
                    #'sdsd': 19.519,
                    #'nni_50': 24,
                    #'pnni_50': 2.4,
                    #'nni_20': 225,
                    #'pnni_20': 22.5,
                    #'rmssd': 19.519,
                    #'median_nni': 722.5,
                    #'range_nni': 249,
                    #'cvsd': 0.0272,
                    #'cvnni': 0.060,
                    #'mean_hr': 83.847,
                    #'max_hr': 101.694,
                    #'min_hr': 71.513,
                    #'std_hr': 5.196}


                    #calcolo lo scarto quadratico medio per HRV
                    sq_diff = np.square(values2 - np.mean(values2))
                    rms = np.sqrt(np.mean(sq_diff))
                    
                    #calcolo lo scarto quadratico medio per HRV senza picchi
                    sq_diff2 = np.square(valori_senza_picchi - np.mean(valori_senza_picchi))
                    rms2 = np.sqrt(np.mean(sq_diff2))

                    #calcolo lo scarto quadratico medio per HRV senza picchi con funzione importata
                    
                    
                    # Aggiorna i tre ultimi valori letti
                    last_values.pop(0)
                    last_values.append(f'Time:{value2:.2f}, GSR: {value3:.2f}, Battiti: {value1:.2f},\n HRV:{rms:.2f}, HRV senza picchi:{rms2:.2f}, SDNN:{sd_nn:.2f},\n RMSSD:{rmssd:.2f}, minHR:{min_hr:.2f}, maxHR:{max_hr:.2f}')

                    # Aggiorna l'interfaccia grafica con gli ultimi i valori letti e calcolati
                    window['-LAST_VALUES-'].update('\n'.join(last_values))

                    # Aggiorna l'interfaccia grafica con il timer
                    window['-TIMER-'].update(timenow)

                    
                    
                   
                                    
                except ValueError:
                    continue

    except Exception as e:
        sg.popup(f"Errore di lettura seriale: {e}")
           
        continue

# Termina il thread del grafico e chiude la porta seriale
graph_running = False#graph_thread.join()

if ser:
    ser.close()

# Chiude la finestra dell'interfaccia grafica
window.close()
