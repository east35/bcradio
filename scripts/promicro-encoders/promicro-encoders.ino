#include <Keyboard.h>

// Pin assignments
#define TUNING_A  2
#define TUNING_B  3
#define TUNING_SW 4
#define VOLUME_A  7
#define VOLUME_B  8
#define VOLUME_SW 9

// Debounce time for push buttons (ms)
#define DEBOUNCE_MS 50

volatile int tuningDelta = 0;
volatile int volumeDelta = 0;

void tuningISR() {
  if (digitalRead(TUNING_A) == digitalRead(TUNING_B))
    tuningDelta++;
  else
    tuningDelta--;
}

void volumeISR() {
  if (digitalRead(VOLUME_A) == digitalRead(VOLUME_B))
    volumeDelta++;
  else
    volumeDelta--;
}

void setup() {
  pinMode(TUNING_A,  INPUT_PULLUP);
  pinMode(TUNING_B,  INPUT_PULLUP);
  pinMode(TUNING_SW, INPUT_PULLUP);
  pinMode(VOLUME_A,  INPUT_PULLUP);
  pinMode(VOLUME_B,  INPUT_PULLUP);
  pinMode(VOLUME_SW, INPUT_PULLUP);

  attachInterrupt(digitalPinToInterrupt(TUNING_A), tuningISR, CHANGE);
  attachInterrupt(digitalPinToInterrupt(VOLUME_A), volumeISR, CHANGE);

  Keyboard.begin();
}

void sendKey(uint8_t key) {
  Keyboard.press(key);
  delay(10);
  Keyboard.release(key);
}

void loop() {
  // Tuning encoder
  if (tuningDelta != 0) {
    noInterrupts();
    int delta = tuningDelta;
    tuningDelta = 0;
    interrupts();
    if (delta > 0) sendKey(KEY_RIGHT_ARROW);
    else           sendKey(KEY_LEFT_ARROW);
  }

  // Volume encoder
  if (volumeDelta != 0) {
    noInterrupts();
    int delta = volumeDelta;
    volumeDelta = 0;
    interrupts();
    if (delta > 0) sendKey(KEY_UP_ARROW);
    else           sendKey(KEY_DOWN_ARROW);
  }

  // Tuning push
  static bool tuningWasPressed = false;
  static unsigned long tuningPressTime = 0;
  bool tuningPressed = digitalRead(TUNING_SW) == LOW;
  if (tuningPressed && !tuningWasPressed && millis() - tuningPressTime > DEBOUNCE_MS) {
    sendKey(KEY_RETURN);
    tuningPressTime = millis();
  }
  tuningWasPressed = tuningPressed;

  // Volume push
  static bool volumeWasPressed = false;
  static unsigned long volumePressTime = 0;
  bool volumePressed = digitalRead(VOLUME_SW) == LOW;
  if (volumePressed && !volumeWasPressed && millis() - volumePressTime > DEBOUNCE_MS) {
    sendKey(' ');
    volumePressTime = millis();
  }
  volumeWasPressed = volumePressed;

  delay(1);
}
