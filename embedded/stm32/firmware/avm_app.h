#pragma once

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
  float t;
  float x;
  float y;
  float vx;
  float vy;
  float tx;
  float ty;
  float ex;
  float ey;
} AvmState;

void avm_app_init(void);
void avm_app_set_pid(float kp, float ki, float kd);
void avm_app_set_target(float x, float y);
void avm_app_reset(float x, float y);
void avm_app_step(float dt);
AvmState avm_app_state(void);
int avm_app_handle_line(const char* line, char* reply, int reply_cap);

#ifdef __cplusplus
}
#endif
