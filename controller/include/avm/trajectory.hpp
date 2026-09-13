#pragma once

#include "avm/types.hpp"

#include <vector>

namespace avm {

class TrapezoidalPlanner {
 public:
  explicit TrapezoidalPlanner(MotionLimits limits = {});

  void set_limits(const MotionLimits& limits);
  const MotionLimits& limits() const { return limits_; }

  std::vector<TrajectoryPoint> plan_segment(const Vec2& start, const Vec2& goal, double t0 = 0.0) const;
  std::vector<TrajectoryPoint> plan_waypoints(const std::vector<Vec2>& waypoints, double t0 = 0.0) const;

 private:
  MotionLimits limits_{};
};

}  // namespace avm
