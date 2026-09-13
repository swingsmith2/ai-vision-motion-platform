#include "avm_app.h"

#ifndef LED_BUILTIN
#define LED_BUILTIN PA5
#endif
#ifndef PIN_AXIS_X
#define PIN_AXIS_X PA6
#endif
#ifndef PIN_AXIS_Y
#define PIN_AXIS_Y PA7
#endif

static const float kDt = 0.002f;
static const float kTable = 0.40f;
static char line[96];
static uint8_t line_len = 0;

static int pos_to_pwm(float meters) {
  float n = meters / kTable;
  if (n < 0.0f) n = 0.0f;
  if (n > 1.0f) n = 1.0f;
  return (int)(n * 255.0f);
}

void setup() {
  Serial.begin(115200);
  pinMode(LED_BUILTIN, OUTPUT);
  pinMode(PIN_AXIS_X, OUTPUT);
  pinMode(PIN_AXIS_Y, OUTPUT);
  avm_app_init();
  Serial.println("AVM STM32 Nucleo-C031 ready");
  Serial.println("CMD T x y | P kp ki kd | R | S");
}

void loop() {
  while (Serial.available() > 0) {
    const char ch = (char)Serial.read();
    if (ch == '\n' || ch == '\r') {
      if (line_len > 0) {
        line[line_len] = 0;
        char reply[160];
        if (avm_app_handle_line(line, reply, (int)sizeof(reply))) {
          Serial.println(reply);
        }
        line_len = 0;
      }
    } else if (line_len + 1 < sizeof(line)) {
      line[line_len++] = ch;
    }
  }

  avm_app_step(kDt);
  const AvmState s = avm_app_state();
  analogWrite(PIN_AXIS_X, pos_to_pwm(s.x));
  analogWrite(PIN_AXIS_Y, pos_to_pwm(s.y));
  const float err = s.ex * s.ex + s.ey * s.ey;
  digitalWrite(LED_BUILTIN, err < 0.002f * 0.002f ? HIGH : LOW);
  delay(2);
}
