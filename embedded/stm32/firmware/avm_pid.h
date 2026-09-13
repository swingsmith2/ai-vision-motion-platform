#pragma once

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
  float kp;
  float ki;
  float kd;
  float out_min;
  float out_max;
  float i_min;
  float i_max;
  float integral;
  float prev_error;
  int has_prev;
} AvmPid;

void avm_pid_init(AvmPid* pid, float kp, float ki, float kd);
void avm_pid_reset(AvmPid* pid);
float avm_pid_update(AvmPid* pid, float error, float dt);

#ifdef __cplusplus
}
#endif
