#include "Arduino_RouterBridge.h"
#include <Arduino_LED_Matrix.h>

Arduino_LED_Matrix matrix;

int timeshow = 0;
int todisplay = true;
// Icona semplice (un punto/cerchio) da mostrare quando viene rilevato un oggetto
uint8_t detectionIcon[104] = {
    0,0,0,0,0,0,0,0,0,0,0,0,0,
    1,0,1,1,1,1,1,0,0,1,1,1,0,
    1,0,0,0,1,0,0,0,1,0,0,0,1,
    1,0,0,0,1,0,0,0,1,0,0,0,0,
    1,0,0,0,1,0,0,0,0,1,1,1,0,
    1,0,0,0,1,0,0,0,0,0,0,0,1,
    1,0,0,0,1,0,0,0,1,0,0,0,1,
    1,0,0,0,1,0,0,0,0,1,1,1,0
};

uint8_t blank[104] = {0}; // matrice spenta

void setup() {
    matrix.begin();
    matrix.setGrayscaleBits(1);

    Bridge.begin();
    // provide_safe perché tocca l'hardware della matrice (esegue nel loop principale)
    Bridge.provide_safe("showDetection", showDetection);
}

void loop() {
    // niente da fare qui, gestito dal callback
    if (timeshow > 0){
      if(todisplay){
         matrix.draw(detectionIcon);
         todisplay = false;
      }
      timeshow-=1;
    } else {
        if(!todisplay){
           matrix.draw(blank); // spegne la matrice
          todisplay = true;
        }
    }
  delay(1);
}

void showDetection() {
    timeshow = 1000;
//    matrix.draw(detectionIcon);
//    delay(1000);        // tempo di visualizzazione
//    matrix.draw(blank); // spegne la matrice
}