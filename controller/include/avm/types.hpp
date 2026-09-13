#pragma once

#include <cmath>
#include <string>
#include <vector>

namespace avm {

struct Vec2 {
  double x = 0.0;
  double y = 0.0;

  Vec2() = default;
  Vec2(double x_, double y_) : x(x_), y(y_) {}

  Vec2 operator+(const Vec2& o) const { return {x + o.x, y + o.y}; }
  Vec2 operator-(const Vec2& o) const { return {x - o.x, y - o.y}; }
  Vec2 operator*(double s) const { return {x * s, y * s}; }

  double norm() const { return std::hypot(x, y); }
};

struct Pose2D {
  double x = 0.0;
  double y = 0.0;
  double yaw = 0.0;
};

struct Twist2D {
  double vx = 0.0;
  double vy = 0.0;
};

struct TrajectoryPoint {
  double t = 0.0;
  Pose2D pose;
  Twist2D twist;
  double ax = 0.0;
  double ay = 0.0;
};

struct MotionLimits {
  double vmax = 0.40;  // m/s
  double amax = 1.20;  // m/s^2
};

struct PidGains {
  double kp = 80.0;
  double ki = 8.0;
  double kd = 6.0;
};

struct PidLimits {
  double out_min = -12.0;
  double out_max = 12.0;
  double integral_min = -2.0;
  double integral_max = 2.0;
};

struct PlantParams {
  double mass = 0.80;        // kg equivalent
  double damping = 4.50;     // N·s/m
  double force_limit = 20.0; // N
};

struct AxisState {
  double pos = 0.0;
  double vel = 0.0;
  double acc = 0.0;
  double force = 0.0;
  double target = 0.0;
};

struct GantryState {
  double t = 0.0;
  AxisState x;
  AxisState y;

  Vec2 position() const { return {x.pos, y.pos}; }
  Vec2 velocity() const { return {x.vel, y.vel}; }
  Vec2 target() const { return {x.target, y.target}; }
};

struct Sample {
  double t = 0.0;
  double x = 0.0;
  double y = 0.0;
  double vx = 0.0;
  double vy = 0.0;
  double tx = 0.0;
  double ty = 0.0;
  double ex = 0.0;
  double ey = 0.0;
};

inline double clamp(double v, double lo, double hi) {
  return v < lo ? lo : (v > hi ? hi : v);
}

}  // namespace avm
