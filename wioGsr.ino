
#include <math.h>     // Includi la libreria math per le funzioni matematiche standard
#include "TFT_eSPI.h" //include TFT LCD library
#include <SPI.h>
#include <Seeed_FS.h>
#include "SD/Seeed_SD.h"
#include "seeed_line_chart.h"

#include <SparkFunBQ27441.h>
#define FF17 &FreeSans9pt7b
const unsigned int BATTERY_CAPACITY = 650; // Set Wio

File myFile;
TFT_eSPI tft; // initialize TFT LCD
TFT_eSprite spr = TFT_eSprite(&tft);



boolean recording = false;
const int GSR = A0;
boolean led_state = LOW;
unsigned long previousMillis = 0;
unsigned long sub; /*valore millisecondi tra un battito e l'altro*/
bool data_effect = true;
boolean serialSending=false;
unsigned int heart_rate;
int sensorValue = 0;
int gsr_average = 0;
int gsrIndex = 0;
int hrIndex = 0;
float ohm;
float conductance;
const int max_heartpluse_duty = 2000; // min 30 battiti
const int min_heartpluse_duty = 400;  // max 150 battiti
double hrvRms;
boolean hrActive = HIGH;
boolean gsrActive = HIGH;
doubles gsr_data, emg_data;
/*SETUP*/


void setup()
{
    
    pinMode(WIO_KEY_A, INPUT_PULLUP);
    pinMode(WIO_KEY_B, INPUT_PULLUP);
    pinMode(WIO_KEY_C, INPUT_PULLUP);

   
    pinMode(GSR, INPUT); // GSR
    Serial.begin(9600);
    tft.begin();                 // start TFT LCD
    tft.setRotation(3);          // set screen rotation
    tft.fillScreen(TFT_BLACK);   // fill background
    tft.setTextColor(TFT_WHITE); // set text color
    tft.setTextSize(1);          // set text size
    spr.createSprite(TFT_HEIGHT -50, TFT_WIDTH); //create sprite

    //attachInterrupt(digitalPinToInterrupt(2), interrupt, RISING);

    /*INIZIALIZZO SCHEDA SD*/
    tft.drawString("INIZIALIZZO SCHEDA SD", 5, 2);
    delay(1000);
    if (!SD.begin(SDCARD_SS_PIN, SDCARD_SPI))
    {
        tft.drawString("INIZIALIZZAZIONE SCHEDA SD FALLITA", 5, 20);
        while (1);
    }
    tft.drawString("INIZIALIZZAZIONE SCHEDA SD RIUSCITA", 5, 50);
    delay(2000);
    tft.fillScreen(TFT_BLACK); // fill background

    setupBQ27441();
  tft.setTextColor(TFT_GREEN);
  tft.setCursor((320 - tft.textWidth("Battery Initialised!"))/2, 120);
  tft.print("Battery Initialised!");
  delay(1000);

    /*Fine inizializzazione*/
   

}

/*Funzione principale*/
void loop()
{

if (digitalRead(WIO_KEY_C) == LOW) {
    serialSending=!serialSending;
    delay(500);
   }

if (digitalRead(WIO_KEY_A) == LOW) {
    recording=!recording;
    delay(500);
   }

if (digitalRead(WIO_KEY_B) == LOW) {
    
  // Per svuotare completamente la serie di dati
  while (!gsr_data.empty()) {
      gsr_data.pop();  // Rimuovi l'ultimo elemento
    }
  }
   
gsr(); /*richiamo funzione lettura dati*/
printBatteryStats();
delay(1000);
}



void display_line_chart(int header_y, const char* header_title, int chart_width, int chart_height, doubles data, uint32_t graph_color, uint32_t line_color){
  // Define the line graph title settings:
  auto header =  text(0, header_y)
                 .value(header_title)
                 .align(center)
                 .valign(vcenter)
                 .width(chart_width)
                 .color(tft.color565(243,208,296))
                 .thickness(2);
  // Define the header height and draw the line graph title. 
  header.height(header.font_height() * 2);
  header.draw();
  // Define the line chart settings:
  auto content = line_chart(0, header.height() + header_y);
  content
  .height(chart_height) // the actual height of the line chart
  .width(chart_width) // the actual width of the line chart
  .based_on(0.0) // the starting point of the y-axis must be float
  .show_circle(false) // drawing a circle at each point, default is on
  .value(data) // passing the given data array to the line graph
  .color(line_color) // setting the line color 
  .x_role_color(graph_color) // setting the line graph color
  .x_tick_color(graph_color)
  .y_role_color(graph_color)
  .y_tick_color(graph_color)
  .draw();
}



/*Funzione lettura dati*/
void gsr()
{

    unsigned long currentMillis = millis();

    //if (currentMillis - previousMillis >= 1)
    //{
        previousMillis = currentMillis;
        long sum = 0;
        for (int i = 0; i < 2000; i++) // Average the 10 measurements to remove the glitch
        {
            sensorValue = analogRead(GSR);
            sum += sensorValue;
            //delay(1);
        }
        gsr_average = sum / 2000;
        ohm = ((1024.0 + (2.0 * gsr_average)) * 10000.0) / (515.0 - gsr_average);
        conductance = 1000000 / ohm;
        // gsrSeries[gsrIndex][0]=currentMillis; /*Inserisco il timestamp*/
        // gsrSeries[gsrIndex][1]=conductance; /*Inserisco la conduttanza*/

        gsrIndex = gsrIndex + 1;
        gsr_data.push(conductance);
    //}

    // Initialize the sprite.
    spr.fillSprite(black);

    if(gsr_data.size() == 300) gsr_data.pop();
    
    tft.fillRect(85, 2, 249, 100, TFT_BLACK); // Cancella rettangolo 

    //PULSANTE SERIALE
    tft.fillRect(1, 2, 50, 10, TFT_BLUE);
    tft.setTextSize(1);          // set text size
    tft.drawString("SER:", 5, 2);

    
    //PULSANTE CANCELLA GRAFICO
    tft.fillRect(68, 2, 50, 10, TFT_BLUE);
    tft.setTextSize(1);          // set text size
    tft.drawString("CLEAN", 76, 2);
    
    //PULSANTE RECORD
    tft.fillRect(150, 2, 50, 10, TFT_BLUE);
    tft.setTextSize(1);          // set text size
    tft.drawString("CSV:", 152, 2);
    
    
    
    
    //Disegna grafico
    display_line_chart(20, "GSR->", TFT_HEIGHT-50, 100, gsr_data, red, tft.color565(165,40,44));
    spr.pushSprite(20, 100);
    spr.setTextColor(red);
    delay(50);

    //tft.fillRect(100, 2, 150, 150, TFT_BLACK); // Cancella rettangolo
    //tft.setCursor(100, 2);
    //tft.print(conductance, 2); // draw float
    tft.setTextSize(2);
    
    tft.setCursor(200, 128);
    tft.print(conductance, 2); // draw float
    tft.setCursor(100, 50);
    
    
    if (serialSending==true)
      {
      tft.setTextSize(1);
      tft.drawString("ON  ", 33, 2);  
      Serial.print(gsrIndex);
      Serial.print(",");
      Serial.print(currentMillis);
      Serial.print(",");
      Serial.println(conductance);
     
      }
      else if (serialSending == false)
      {
         tft.setTextSize(1);
      tft.drawString("OFF", 33, 2);
        }
    
    if (recording == true) {
       tft.setTextSize(1);
       tft.drawString("ON ", 180, 2);
       tft.drawCircle(210,7,5,TFT_RED); //A black circle origin at (160, 120) 
       tft.fillCircle(210,7,5,TFT_RED); 
      
       /*scrivo i dati del GSR nel file CSV*/
       myFile = SD.open("gsr.csv", FILE_APPEND);
       if (myFile)
        {

          myFile.print("GSR");
          myFile.print(",");
          myFile.print(gsrIndex);
          myFile.print(",");
          myFile.print(currentMillis);
          myFile.print(",");
          myFile.println(conductance);
          // close the file:
          myFile.close();
        }
    else
    {
        // inserire qui un eventuale messaggio di errore
        // Serial.println("error opening test.txt");
    }  
     
      
   }
   else if (recording == false)
       {
        tft.setTextSize(1);
        tft.drawString("OFF", 180, 2);
        tft.fillCircle(210,7,5,TFT_BLACK); 
      
        tft.drawCircle(210,7,5,TFT_RED); //A black circle origin at (160, 120) 
        
        
        } 
    
}




void setupBQ27441(void)
{
  // Use lipo.begin() to initialize the BQ27441-G1A and confirm that it's
  // connected and communicating.
  if (!lipo.begin()) // begin() will return true if communication is successful
  {
  // If communication fails, print an error message and loop forever.
    Serial.println("Error: Unable to communicate with BQ27441.");
    Serial.println("  Check wiring and try again.");
    Serial.println("  (Battery must be plugged into Battery Babysitter!)");
    tft.setTextColor(TFT_RED);
    tft.setCursor((320 - tft.textWidth("Battery Not Initialised!"))/2, 120);
    tft.print("Battery Not Initialised!");
    while (1) ;
  }
  Serial.println("Connected to BQ27441!");

  // Uset lipo.setCapacity(BATTERY_CAPACITY) to set the design capacity
  // of your battery.
  lipo.setCapacity(BATTERY_CAPACITY);
}

void printBatteryStats()
{
  // Read battery stats from the BQ27441-G1A
 
  unsigned int soc = lipo.soc();  // Read state-of-charge (%)
 
  
  // Data
   tft.setTextSize(2);
   tft.fillRect(250, 2, 250, 100, TFT_BLACK);// Cancella rettangolo 
   tft.setCursor(260, 2);
   tft.print(soc); // draw float
    
    tft.drawString("%",290,2);
    
    
  
}
