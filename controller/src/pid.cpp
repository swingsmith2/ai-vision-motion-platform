#include "avm/pid.hpp"

namespace avm {

PidController::PidController(const PidGains& gains, const PidLimits& limits)
    : gains_(gains), limits_(limits) {}

void PidController::set_gains(const PidGains& gains) { gains_ = gains; }

void PidController::set_limits(const PidLimits& limits) { limits_ = limits; }

void PidController::reset() {
  integral_ = 0.0;
  prev_error_ = 0.0;
  has_prev_ = false;
}

double PidController::update(double error, double dt) {
  if (dt <= 0.0) {
    return 0.0;
  }

  integral_ = clamp(integral_ + error * dt, limits_.integral_min, limits_.integral_max);
  const double derivative = has_prev_ ? (error - prev_error_) / dt : 0.0;
  prev_error_ = error;
  has_prev_ = true;

  const double output = gains_.kp * error + gains_.ki * integral_ + gains_.kd * derivative;
  return clamp(output, limits_.out_min, limits_.out_max);
}

}  // namespace avm
