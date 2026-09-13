#include "avm_app.h"

#include "avm_pid.h"

#include <math.h>
#include <stdio.h>
#include <string.h>

typedef struct {
  float pos;
  float vel;
  float target;
} Axis;

static AvmPid pid_x_;
static AvmPid pid_y_;
static Axis axis_x_;
static Axis axis_y_;
static float t_;
static const float kMass = 0.80f;
static const float kDamp = 4.50f;
static const float kForceLim = 20.0f;

static float clampf(float v, float lo, float hi) {
  if (v < lo) {
    return lo;
  }
  if (v > hi) {
    return hi;
  }
  return v;
}

static void step_axis(Axis* axis, AvmPid* pid, float dt) {
  const float force = clampf(avm_pid_update(pid, axis->target - axis->pos, dt), -kForceLim, kForceLim);
  const float acc = (force - kDamp * axis->vel) / kMass;
  axis->vel += acc * dt;
  axis->pos += axis->vel * dt;
}

void avm_app_init(void) {
  avm_pid_init(&pid_x_, 80.0f, 8.0f, 6.0f);
  avm_pid_init(&pid_y_, 80.0f, 8.0f, 6.0f);
  avm_app_reset(0.0f, 0.0f);
}

void avm_app_set_pid(float kp, float ki, float kd) {
  avm_pid_init(&pid_x_, kp, ki, kd);
  avm_pid_init(&pid_y_, kp, ki, kd);
}

void avm_app_set_target(float x, float y) {
  axis_x_.target = x;
  axis_y_.target = y;
}

void avm_app_reset(float x, float y) {
  avm_pid_reset(&pid_x_);
  avm_pid_reset(&pid_y_);
  t_ = 0.0f;
  axis_x_.pos = x;
  axis_y_.pos = y;
  axis_x_.vel = 0.0f;
  axis_y_.vel = 0.0f;
  axis_x_.target = x;
  axis_y_.target = y;
}

void avm_app_step(float dt) {
  step_axis(&axis_x_, &pid_x_, dt);
  step_axis(&axis_y_, &pid_y_, dt);
  t_ += dt;
}

AvmState avm_app_state(void) {
  AvmState s;
  s.t = t_;
  s.x = axis_x_.pos;
  s.y = axis_y_.pos;
  s.vx = axis_x_.vel;
  s.vy = axis_y_.vel;
  s.tx = axis_x_.target;
  s.ty = axis_y_.target;
  s.ex = axis_x_.target - axis_x_.pos;
  s.ey = axis_y_.target - axis_y_.pos;
  return s;
}

int avm_app_handle_line(const char* line, char* reply, int reply_cap) {
  if (!line || !reply || reply_cap < 8) {
    return 0;
  }
  reply[0] = 0;
  if (line[0] == 0 || line[0] == '#') {
    return 0;
  }
  if (line[0] == 'T' || line[0] == 't') {
    float x = 0.0f;
    float y = 0.0f;
    if (sscanf(line + 1, "%f %f", &x, &y) < 2) {
      snprintf(reply, (size_t)reply_cap, "ERR target");
      return 1;
    }
    avm_app_set_target(x, y);
    snprintf(reply, (size_t)reply_cap, "OK T %.4f %.4f", x, y);
    return 1;
  }
  if (line[0] == 'P' || line[0] == 'p') {
    float kp = 80.0f;
    float ki = 8.0f;
    float kd = 6.0f;
    if (sscanf(line + 1, "%f %f %f", &kp, &ki, &kd) < 3) {
      snprintf(reply, (size_t)reply_cap, "ERR pid");
      return 1;
    }
    avm_app_set_pid(kp, ki, kd);
    snprintf(reply, (size_t)reply_cap, "OK P %.1f %.1f %.1f", kp, ki, kd);
    return 1;
  }
  if (line[0] == 'R' || line[0] == 'r') {
    avm_app_reset(0.0f, 0.0f);
    snprintf(reply, (size_t)reply_cap, "OK RESET");
    return 1;
  }
  if (line[0] == 'S' || line[0] == 's') {
    const AvmState s = avm_app_state();
    snprintf(reply, (size_t)reply_cap, "POS t=%.3f x=%.4f y=%.4f ex=%.4f ey=%.4f", s.t, s.x, s.y, s.ex, s.ey);
    return 1;
  }
  if (line[0] == 'H' || line[0] == 'h' || line[0] == '?') {
    snprintf(reply, (size_t)reply_cap, "CMD T x y | P kp ki kd | R | S");
    return 1;
  }
  snprintf(reply, (size_t)reply_cap, "ERR unknown");
  return 1;
}
