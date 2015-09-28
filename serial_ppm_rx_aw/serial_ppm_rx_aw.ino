#include <TimerOne.h>

#define CHANNELS 8

#define MIN_PULSE_TIME 1000     // Minimum [us] (normal ops)
#define MAX_PULSE_TIME 2000     // Maximum [us] (normal ops)
#define NEUTRAL_PULSE_TIME 1500 // Neutral [us] (normal ops)
#define SYNC_PULSE_TIME 4000    // 4000us
#define PULSE_OFF_TIME 300      // 300us
#define FAILED_PULSE_TIME 900   // Abnormal pulse [ms] (lost)

#define SERIAL_BAUD 38400

#define PIN_LED 13
#define PIN_PPM 9

#define RECEIVER_TIMEOUT 1500 // 1.5s
#define MIN_RECEIVER_VALUE 0
#define MAX_RECEIVER_VALUE 250

const unsigned int defaultPulseWidths[CHANNELS] = {
  NEUTRAL_PULSE_TIME, // Roll
  NEUTRAL_PULSE_TIME, // Pitch
  MIN_PULSE_TIME,     // Throttle
  NEUTRAL_PULSE_TIME, // Yaw
  MAX_PULSE_TIME,     // AUX1
  MAX_PULSE_TIME,     // AUX2
  MAX_PULSE_TIME,     // AUX3
  MAX_PULSE_TIME      // AUX4
};

const unsigned int noComPulseWidths[CHANNELS] = {
  NEUTRAL_PULSE_TIME, // ROLL
  NEUTRAL_PULSE_TIME, // PITCH
  FAILED_PULSE_TIME,  // THROTTLE
  NEUTRAL_PULSE_TIME, // YAW
  MAX_PULSE_TIME,     // AUX1
  MAX_PULSE_TIME,     // AUX2
  MAX_PULSE_TIME,     // AUX3
  MAX_PULSE_TIME,     // AUX4
};


// Inbound data is: [roll, pitch, throttle, yaw, aux1, aux2, aux3, aux4]
const int channelMap[CHANNELS] = {0, 1, 2, 3, 4, 5, 6, 7};

volatile boolean toggle = 1;
unsigned int pulseWidths[CHANNELS];
byte buffer[CHANNELS];
int bytesReceived;
byte currentByte;
unsigned long lastReceived = 0;
boolean linked = false;
boolean lost = false;

// Start-up positions
void setDefaultPulseWidths() {
  for (int i=0; i<CHANNELS; i++) {
    pulseWidths[i] = defaultPulseWidths[i];
  }
}

// Allows autopilot to detect loss of transmitter
void setLostPulseWidths() {
  for (int i=0; i<CHANNELS; i++) {
    pulseWidths[i] = defaultPulseWidths[i];
  }
}


// Begins on reset or power-on
void setup() {
  pinMode(PIN_LED, OUTPUT);
  pinMode(PIN_PPM, OUTPUT);

  Serial.begin(38400);
  
  setDefaultPulseWidths();
  
  // Start timer with sync pulse
  Timer1.initialize(SYNC_PULSE_TIME);
  Timer1.attachInterrupt(isr_sendPulses);
  isr_sendPulses();
}

// Main execution
void loop() {
  handleSerial();
  checkLinked();
  checkLostReception();
  signalState();
} 

void handleSerial() {
  // Handle Serial Data
  if (Serial.available()) {
    lastReceived = millis();
    currentByte = Serial.read();

    if (currentByte == 254) {
      // Either packet is done, or we got corrupt data. Reset the packet
      bytesReceived = 0;
    } else {
      buffer[bytesReceived] = currentByte;
      bytesReceived++;
    }

    if (bytesReceived == CHANNELS) {
      bytesReceived = 0;
      linked = true;

      // Convert char (0-250) to pulse width (1000-2000)
      for (int i=0; i<CHANNELS; i++) {
        pulseWidths[i] = map(buffer[i], MIN_RECEIVER_VALUE, MAX_RECEIVER_VALUE, 
                                        MIN_PULSE_TIME, MAX_PULSE_TIME);
      }
    }
  }
}

void checkLinked() {
  // Not linked yet (no packets received) or lost reception, blink the LED
  if(!linked) {
    if(lost) {
      setLostPulseWidths();
    } else {
      setDefaultPulseWidths();
    }
  } else {
    digitalWrite(PIN_LED, HIGH);
  }
}

void checkLostReception() {
  // Check if we lost reception
  if(linked && lastReceived > 0 &&  millis() - lastReceived > RECEIVER_TIMEOUT) {
    linked = false;
    lost = true;
  }
}

void signalState() {
  if (lost) {
    digitalWrite(PIN_LED, HIGH);
    delay(100);
    digitalWrite(PIN_LED, LOW);
    delay(100);
  } else if(!linked) {
    digitalWrite(PIN_LED, HIGH);
    delay(1000);
    digitalWrite(PIN_LED, LOW);
    delay(1000);
  } else {
    digitalWrite(PIN_LED, HIGH);
  }
}

// Sync pulse first
volatile int currentChannel = 0;

void isr_sendPulses() {
  if(toggle) {
    digitalWrite(PIN_PPM, LOW);
    Timer1.setPeriod(PULSE_OFF_TIME);
    toggle = 0;
  } else {
    digitalWrite(PIN_PPM, HIGH);
    toggle = 1;
    if(currentChannel < 8) {
      Timer1.setPeriod(pulseWidths[channelMap[currentChannel]]-PULSE_OFF_TIME);
      currentChannel++;
    } else {
      Timer1.setPeriod(SYNC_PULSE_TIME);
      currentChannel = 0;
    }
  }
}
