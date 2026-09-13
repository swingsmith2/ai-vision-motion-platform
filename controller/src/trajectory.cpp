#include "avm/trajectory.hpp"

#include <algorithm>

namespace avm {

TrapezoidalPlanner::TrapezoidalPlanner(MotionLimits limits) : limits_(limits) {}

void TrapezoidalPlanner::set_limits(const MotionLimits& limits) { limits_ = limits; }

std::vector<TrajectoryPoint> TrapezoidalPlanner::plan_segment(const Vec2& start,
                                                              const Vec2& goal,
                                                              double t0) const {
  std::vector<TrajectoryPoint> points;
  const Vec2 delta = goal - start;
  const double distance = delta.norm();
  if (distance < 1e-9) {
    TrajectoryPoint p;
    p.t = t0;
    p.pose.x = start.x;
    p.pose.y = start.y;
    points.push_back(p);
    return points;
  }

  const Vec2 dir = delta * (1.0 / distance);
  const double vmax = std::max(limits_.vmax, 1e-6);
  const double amax = std::max(limits_.amax, 1e-6);
  const double t_acc = vmax / amax;
  const double d_acc = 0.5 * amax * t_acc * t_acc;

  double t_cruise = 0.0;
  double t_total = 0.0;
  double v_peak = vmax;
  if (2.0 * d_acc >= distance) {
    v_peak = std::sqrt(distance * amax);
    const double t_tri = v_peak / amax;
    t_total = 2.0 * t_tri;
  } else {
    t_cruise = (distance - 2.0 * d_acc) / vmax;
    t_total = 2.0 * t_acc + t_cruise;
  }

  const double dt = 0.002;
  const int n = std::max(2, static_cast<int>(std::ceil(t_total / dt)) + 1);
  points.reserve(static_cast<size_t>(n));

  for (int i = 0; i < n; ++i) {
    const double tau = std::min(t_total, i * dt);
    double s = 0.0;
    double v = 0.0;
    double a = 0.0;
    if (2.0 * d_acc >= distance) {
      const double t_tri = v_peak / amax;
      if (tau <= t_tri) {
        a = amax;
        v = amax * tau;
        s = 0.5 * amax * tau * tau;
      } else {
        const double td = tau - t_tri;
        a = -amax;
        v = v_peak - amax * td;
        s = 0.5 * amax * t_tri * t_tri + v_peak * td - 0.5 * amax * td * td;
      }
    } else if (tau <= t_acc) {
      a = amax;
      v = amax * tau;
      s = 0.5 * amax * tau * tau;
    } else if (tau <= t_acc + t_cruise) {
      a = 0.0;
      v = vmax;
      s = d_acc + vmax * (tau - t_acc);
    } else {
      const double td = tau - t_acc - t_cruise;
      a = -amax;
      v = vmax - amax * td;
      s = d_acc + vmax * t_cruise + vmax * td - 0.5 * amax * td * td;
    }

    s = clamp(s, 0.0, distance);
    TrajectoryPoint p;
    p.t = t0 + tau;
    const Vec2 pos = start + dir * s;
    p.pose.x = pos.x;
    p.pose.y = pos.y;
    p.twist.vx = dir.x * v;
    p.twist.vy = dir.y * v;
    p.ax = dir.x * a;
    p.ay = dir.y * a;
    points.push_back(p);
  }
  return points;
}

std::vector<TrajectoryPoint> TrapezoidalPlanner::plan_waypoints(const std::vector<Vec2>& waypoints,
                                                               double t0) const {
  std::vector<TrajectoryPoint> all;
  if (waypoints.empty()) {
    return all;
  }
  if (waypoints.size() == 1) {
    TrajectoryPoint p;
    p.t = t0;
    p.pose.x = waypoints[0].x;
    p.pose.y = waypoints[0].y;
    all.push_back(p);
    return all;
  }

  double t = t0;
  for (size_t i = 0; i + 1 < waypoints.size(); ++i) {
    auto seg = plan_segment(waypoints[i], waypoints[i + 1], t);
    if (!all.empty() && !seg.empty()) {
      seg.erase(seg.begin());
    }
    if (!seg.empty()) {
      t = seg.back().t;
      all.insert(all.end(), seg.begin(), seg.end());
    }
  }
  return all;
}

}  // namespace avm
