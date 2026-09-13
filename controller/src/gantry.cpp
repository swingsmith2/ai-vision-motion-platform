#include "avm/gantry.hpp"

namespace avm {

GantrySimulator::GantrySimulator() {
  pid_x_.set_gains(PidGains{});
  pid_y_.set_gains(PidGains{});
  pid_x_.set_limits(PidLimits{});
  pid_y_.set_limits(PidLimits{});
}

void GantrySimulator::set_pid(const PidGains& gains) {
  pid_x_.set_gains(gains);
  pid_y_.set_gains(gains);
}

void GantrySimulator::set_limits(const PidLimits& limits) {
  pid_x_.set_limits(limits);
  pid_y_.set_limits(limits);
}

void GantrySimulator::set_plant(const PlantParams& plant) { plant_ = plant; }

void GantrySimulator::reset(const Vec2& pos) {
  pid_x_.reset();
  pid_y_.reset();
  state_ = {};
  state_.x.pos = pos.x;
  state_.y.pos = pos.y;
  state_.x.target = pos.x;
  state_.y.target = pos.y;
}

void GantrySimulator::set_target(const Vec2& target) {
  state_.x.target = target.x;
  state_.y.target = target.y;
}

void GantrySimulator::step_axis(AxisState& axis, PidController& pid, double dt, double v_ref, double a_ref) {
  const double fb = pid.update(axis.target - axis.pos, dt);
  const double ff = plant_.mass * a_ref + plant_.damping * v_ref;
  axis.force = clamp(fb + ff, -plant_.force_limit, plant_.force_limit);
  const double acc = (axis.force - plant_.damping * axis.vel) / std::max(plant_.mass, 1e-6);
  axis.acc = acc;
  axis.vel += acc * dt;
  axis.pos += axis.vel * dt;
}

GantryState GantrySimulator::step(double dt, const Twist2D& twist, double ax, double ay) {
  step_axis(state_.x, pid_x_, dt, twist.vx, ax);
  step_axis(state_.y, pid_y_, dt, twist.vy, ay);
  state_.t += dt;
  return state_;
}

std::vector<Sample> GantrySimulator::follow(const std::vector<TrajectoryPoint>& traj, double dt) {
  std::vector<Sample> samples;
  if (traj.empty()) {
    return samples;
  }
  if (!traj.empty()) {
    reset({traj.front().pose.x, traj.front().pose.y});
  }

  size_t idx = 0;
  double t = traj.front().t;
  const double t_end = traj.back().t;
  samples.reserve(static_cast<size_t>((t_end - t) / dt) + 8);

  while (t <= t_end + 1e-12) {
    while (idx + 1 < traj.size() && traj[idx + 1].t <= t) {
      ++idx;
    }
    const auto& ref = traj[idx];
    set_target({ref.pose.x, ref.pose.y});
    step(dt, ref.twist, ref.ax, ref.ay);

    Sample s;
    s.t = state_.t;
    s.x = state_.x.pos;
    s.y = state_.y.pos;
    s.vx = state_.x.vel;
    s.vy = state_.y.vel;
    s.tx = state_.x.target;
    s.ty = state_.y.target;
    s.ex = s.tx - s.x;
    s.ey = s.ty - s.y;
    samples.push_back(s);
    t += dt;
  }
  return samples;
}

}  // namespace avm
