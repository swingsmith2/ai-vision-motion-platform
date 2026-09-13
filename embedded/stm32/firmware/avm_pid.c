#include "avm_pid.h"

static float clampf(float v, float lo, float hi) {
  if (v < lo) {
    return lo;
  }
  if (v > hi) {
    return hi;
  }
  return v;
}

void avm_pid_init(AvmPid* pid, float kp, float ki, float kd) {
  pid->kp = kp;
  pid->ki = ki;
  pid->kd = kd;
  pid->out_min = -12.0f;
  pid->out_max = 12.0f;
  pid->i_min = -2.0f;
  pid->i_max = 2.0f;
  avm_pid_reset(pid);
}

void avm_pid_reset(AvmPid* pid) {
  pid->integral = 0.0f;
  pid->prev_error = 0.0f;
  pid->has_prev = 0;
}

float avm_pid_update(AvmPid* pid, float error, float dt) {
  if (dt <= 0.0f) {
    return 0.0f;
  }
  pid->integral = clampf(pid->integral + error * dt, pid->i_min, pid->i_max);
  const float derivative = pid->has_prev ? (error - pid->prev_error) / dt : 0.0f;
  pid->prev_error = error;
  pid->has_prev = 1;
  const float out = pid->kp * error + pid->ki * pid->integral + pid->kd * derivative;
  return clampf(out, pid->out_min, pid->out_max);
}
