
#include <math.h> // Includi la libreria math per le funzioni matematiche standard
#include"TFT_eSPI.h" //include TFT LCD library 
#include <SPI.h>
#include <Seeed_FS.h>
#include "SD/Seeed_SD.h"

File myFile;
TFT_eSPI tft; //initialize TFT LCD 

const int GSR = A0;
boolean led_state = LOW;
unsigned long previousMillis = 0;
unsigned long sub; /*valore millisecondi tra un battito e l'altro*/
bool data_effect = true;
unsigned int heart_rate;
int sensorValue = 0;
int gsr_average = 0;
int gsrIndex=0;
int hrIndex=0;
float ohm;
float conductance;
const int max_heartpluse_duty = 2000; //min 30 battiti
const int min_heartpluse_duty = 400; //max 150 battiti
unsigned long gsrSeries[3600][2];
unsigned long hrSeries[3600][3];
double hrvRms;

String sessionOwner;
String sessionName;

/*SETUP*/

void setup() {
  sessionOwner = generateRandomString(10);
  sessionName = generateRandomString(10);

  pinMode(GSR, INPUT); // GSR
  Serial.begin(9600);
  tft.begin(); //start TFT LCD 
  tft.setRotation(3); //set screen rotation 
  tft.fillScreen(TFT_BLACK); //fill background 
  tft.setTextColor(TFT_WHITE); //set text color
  tft.setTextSize(1); //set text size 
  
  attachInterrupt(digitalPinToInterrupt(2), interrupt, RISING);

/*INIZIALIZZO SCHEDA SD*/
  tft.drawString("INIZIALIZZO SCHEDA SD",5,2);
  delay(1000);
  if (!SD.begin(SDCARD_SS_PIN, SDCARD_SPI)) {
    tft.drawString("INIZIALIZZAZIONE SCHEDA SD FALLITA",5,20);
    while (1);
  }
  tft.drawString("INIZIALIZZAZIONE SCHEDA SD RIUSCITA",5,50);
  delay(2000);
  tft.fillScreen(TFT_BLACK); //fill background 
  
/*Fine inizializzazione*/
tft.setTextSize(4);

}


/*Funzione principale*/
void loop() {
  
  delay(1000);
  tft.drawString("GSR:",5,2);
  tft.drawString("HR :",5,50);
  tft.drawString("HRV:",5,100);
    
  gsr(); /*richiamo funzione lettura GSR*/
  
  }


/*Funzione lettura dati*/
void gsr() {
  
  unsigned long currentMillis = millis();
  
  if (currentMillis - previousMillis >= 5) {
    previousMillis = currentMillis;
    long sum = 0;
    for (int i = 0; i < 10; i++)  //Average the 10 measurements to remove the glitch
    {
      sensorValue = analogRead(GSR);
      sum += sensorValue;
      delay(5);
    }
    gsr_average = sum / 10;
    ohm = ((1024.0 + (2.0 * gsr_average)) * 10000.0) / (515.0 - gsr_average);
    conductance = 1000000 / ohm;
    gsrSeries[gsrIndex][0]=currentMillis; /*Inserisco il timestamp*/
    gsrSeries[gsrIndex][1]=conductance; /*Inserisco la conduttanza*/
     
    gsrIndex=gsrIndex+1;
    }

  tft.fillRect(100, 2, 150, 150, TFT_BLACK); // Utilizza il colore di sfondo del tuo display
  tft.setCursor(100, 2);
  tft.print(conductance,2); //draw float
  
  tft.drawNumber(heart_rate,100,50); //draw text string 
  tft.setCursor(100, 100);
  tft.print(hrvRms,2); //draw float
   /*scrivo i dati del GSR nel file CSV*/
   myFile = SD.open("gsr.csv",FILE_APPEND);
   if (myFile) {
    
    myFile.print(sessionName);
    myFile.print(",");
    myFile.print("Simone");
    myFile.print(",");   
    myFile.print("GSR");
    myFile.print(",");
    myFile.print(gsrIndex);
    myFile.print(",");
    myFile.println(conductance);
    // close the file:
    myFile.close();
      
  } else {
    // if the file didn't open, print an error:
    Serial.println("error opening test.txt");
  } 
  }



/*funzione salvataggio dati HRV*/
void send() {
  if (data_effect) {
    heart_rate = 60000 / (sub);
    Serial.print(heart_rate);
    Serial.print(",");
    Serial.print(sub);
    Serial.print(",");
    Serial.println(conductance, 2);
  }
  data_effect = true;
}


float calculateRMS(float values[], int length) {
  float sumOfSquares = 0.0;
  float sum = 0.0;

  // Calcola la somma dei valori
  for (int i = 0; i < length; i++) {
    sum += values[i];
  }

  // Calcola la media dei valori
  float mean = sum / length;

  // Calcola la somma dei quadrati delle differenze
  for (int i = 0; i < length; i++) {
    float diff = values[i] - mean;
    sumOfSquares += pow(diff, 2);
  }

  // Calcola la media dei quadrati delle differenze e calcola la radice quadrata
  float rms = sqrt(sumOfSquares / length);

  return rms;
}



String generateRandomString(int lengthofstring) {
  String characters = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
  String randomString = "";

  for (int i = 0; i < lengthofstring; i++) {
    int randomIndex = random(characters.length());
    char randomChar = characters[randomIndex];
    randomString += randomChar;
  }

  return randomString;
}

String randomString = generateRandomString(10);


/*funzione ricezione dati hrv quando c'è lettura*/ 
void interrupt() {
  static unsigned long previousInterruptMillis = 0; /*Inizializzo la variabile (solo la prima volta, poi permanente in quanto static)*/
  unsigned long currentInterruptMillis = millis();
  static float hrvValues[3600];
  if (currentInterruptMillis - previousInterruptMillis >= max_heartpluse_duty ||
      currentInterruptMillis - previousInterruptMillis <= min_heartpluse_duty)  {
    data_effect = false;
    Serial.println("Nessun dato HR");
    previousInterruptMillis = currentInterruptMillis;
  } else {
    sub = currentInterruptMillis - previousInterruptMillis;
    heart_rate = 60000 / (sub);
    previousInterruptMillis = currentInterruptMillis;
    hrSeries[hrIndex][0]=currentInterruptMillis; /*Inserisco il timestamp*/
    hrSeries[hrIndex][1]=sub; /*Inserisco la conduttanza*/
    hrSeries[hrIndex][2]=heart_rate; /*Inserisco la conduttanza*/
    hrvValues[hrIndex]=sub;
    /*CALCOLO dell'HRV come SCARTO QUADRATICO MEDIO (RMS)*/
    hrvRms = calculateRMS(hrvValues, (hrIndex+1));  
    hrIndex=hrIndex+1;

       /*scrivo i dati del HR nel file CSV*/
   myFile = SD.open("hr.csv",FILE_APPEND);
   if (myFile) {
    
    myFile.print(sessionName);
    myFile.print(",");
    myFile.print("Simone");
    myFile.print(",");   
    myFile.print("HR");
    myFile.print(",");
    myFile.print(hrIndex);
    myFile.print(",");
    myFile.println(sub);
    // close the file:
    myFile.close();
      
  } else {
    // if the file didn't open, print an error:
    Serial.println("error opening test.txt");
  }
    
    send(); /*invio dati in seriale*/
  }
}
