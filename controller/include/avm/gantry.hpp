#pragma once

#include "avm/pid.hpp"
#include "avm/types.hpp"

#include <vector>

namespace avm {

class GantrySimulator {
 public:
  GantrySimulator();

  void set_pid(const PidGains& gains);
  void set_limits(const PidLimits& limits);
  void set_plant(const PlantParams& plant);
  void reset(const Vec2& pos = {});
  void set_target(const Vec2& target);

  GantryState step(double dt, const Twist2D& twist = {}, double ax = 0.0, double ay = 0.0);
  std::vector<Sample> follow(const std::vector<TrajectoryPoint>& traj, double dt);

  const GantryState& state() const { return state_; }

 private:
  void step_axis(AxisState& axis, PidController& pid, double dt, double v_ref, double a_ref);

  PidController pid_x_;
  PidController pid_y_;
  PlantParams plant_{};
  GantryState state_{};
};

}  // namespace avm
