const int GSR = A2;

boolean led_state = LOW;
unsigned long previousMillis = 0;
unsigned long sub;
bool data_effect = true;
unsigned int heart_rate;

int sensorValue = 0;
int gsr_average = 0;
float ohm;
float conductance;

const int max_heartpluse_duty = 2000;

void setup() {
  Serial.begin(9600);
  Serial.println("Please ready your chest belt.");
  delay(5000);
  Serial.println("Heart rate test begin.");
  attachInterrupt(digitalPinToInterrupt(2), interrupt, RISING);
}

void loop() {
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

    if (Serial.available() > 0) {
      char c = Serial.read();
      if (c == 'r') {
        led_state = !led_state;
      }
    }
  }
}

void sum() {
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

void interrupt() {
  static unsigned long previousInterruptMillis = 0;
  unsigned long currentInterruptMillis = millis();
  if (currentInterruptMillis - previousInterruptMillis >= max_heartpluse_duty) {
    data_effect = false;
    Serial.println("Heart rate measure error, test will restart!");
    previousInterruptMillis = currentInterruptMillis;
  } else {
    sub = currentInterruptMillis - previousInterruptMillis;
    previousInterruptMillis = currentInterruptMillis;
    sum();
  }
}
