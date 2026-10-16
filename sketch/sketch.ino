#include "Arduino_RouterBridge.h"
#include <Arduino_LED_Matrix.h>

Arduino_LED_Matrix matrix;

const int MATRIX_ROWS = 8;
const int MATRIX_COLS = 13;

int timeshow = 0;
bool showingIcon = false;

uint8_t blank[104] = {0};

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

// "ERR" da far lampeggiare quando la camera non è rilevata o si verifica un altro errore
uint8_t errorIcon[104] = {
    0,0,0,0,0,0,0,0,0,0,0,0,0,
    1,1,1,0,1,1,0,0,1,1,0,0,0,
    1,0,0,0,1,0,1,0,1,0,1,0,0,
    1,1,1,0,1,1,0,0,1,1,0,0,0,
    1,0,0,0,1,0,1,0,1,0,1,0,0,
    1,1,1,0,1,0,1,0,1,0,1,0,0,
    0,0,0,0,0,0,0,0,0,0,0,0,0,
    0,0,0,0,0,0,0,0,0,0,0,0,0
};

// Stato di errore: ogni showError() estende la finestra, decade da solo se non rinnovato
bool errorActive = false;
unsigned long errorUntil = 0;
const unsigned long ERROR_HOLD_MS = 2000;
unsigned long lastErrBlink = 0;
bool errBlinkOn = false;
const unsigned long ERR_BLINK_INTERVAL_MS = 300;

// Quadrato 2x2 che rimbalza sulla matrice quando nessun oggetto è rilevato
int sqRow = 0;
int sqCol = 0;
int sqDRow = 1;
int sqDCol = 1;
unsigned long lastMove = 0;
const unsigned long MOVE_INTERVAL_MS = 150;

void drawBouncingSquare() {
    uint8_t frame[104] = {0};
    for (int r = 0; r < 2; r++) {
        for (int c = 0; c < 2; c++) {
            frame[(sqRow + r) * MATRIX_COLS + (sqCol + c)] = 1;
        }
    }
    matrix.draw(frame);
}

void updateBouncingSquare() {
    sqRow += sqDRow;
    sqCol += sqDCol;
    if (sqRow <= 0 || sqRow >= MATRIX_ROWS - 2) sqDRow = -sqDRow;
    if (sqCol <= 0 || sqCol >= MATRIX_COLS - 2) sqDCol = -sqDCol;
    sqRow = constrain(sqRow, 0, MATRIX_ROWS - 2);
    sqCol = constrain(sqCol, 0, MATRIX_COLS - 2);
}

void setup() {
    matrix.begin();
    matrix.setGrayscaleBits(1);

    Bridge.begin();
    // provide_safe perché toccano l'hardware della matrice (eseguono nel loop principale)
    Bridge.provide_safe("showDetection", showDetection);
    Bridge.provide_safe("showError", showError);
}

void loop() {
    unsigned long now = millis();

    if (errorActive && now > errorUntil) {
        errorActive = false;
    }

    if (errorActive) {
        if (now - lastErrBlink >= ERR_BLINK_INTERVAL_MS) {
            lastErrBlink = now;
            errBlinkOn = !errBlinkOn;
            matrix.draw(errBlinkOn ? errorIcon : blank);
        }
    } else if (timeshow > 0) {
        if (!showingIcon) {
            matrix.draw(detectionIcon);
            showingIcon = true;
        }
        timeshow -= 1;
    } else {
        showingIcon = false;
        if (now - lastMove >= MOVE_INTERVAL_MS) {
            lastMove = now;
            updateBouncingSquare();
            drawBouncingSquare();
        }
    }
    delay(1);
}

void showDetection() {
    timeshow = 1000;
}

void showError() {
    errorActive = true;
    errorUntil = millis() + ERROR_HOLD_MS;
}
