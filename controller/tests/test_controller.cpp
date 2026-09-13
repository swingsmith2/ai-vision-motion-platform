#include "avm/gantry.hpp"
#include "avm/pid.hpp"
#include "avm/protocol.hpp"
#include "avm/trajectory.hpp"

#include <cmath>
#include <iostream>

namespace {

int g_failed = 0;

void expect(bool cond, const char* msg) {
  if (!cond) {
    std::cerr << "FAIL: " << msg << '\n';
    ++g_failed;
  }
}

}  // namespace

int main() {
  {
    avm::PidController pid({12.0, 0.0, 0.0}, {});
    const double out = pid.update(0.10, 0.01);
    expect(std::fabs(out - 1.20) < 1e-9, "p-only output");
  }

  {
    avm::TrapezoidalPlanner planner({0.4, 1.2});
    const auto traj = planner.plan_segment({0.0, 0.0}, {0.20, 0.00});
    expect(!traj.empty(), "trajectory not empty");
    expect(std::fabs(traj.front().pose.x) < 1e-6, "start x");
    expect(std::fabs(traj.back().pose.x - 0.20) < 2e-3, "end x");
    expect(std::fabs(traj.back().twist.vx) < 2e-2, "end vx near 0");
  }

  {
    avm::TrapezoidalPlanner planner({0.35, 1.0});
    avm::GantrySimulator gantry;
    gantry.set_pid({80.0, 8.0, 6.0});
    const auto traj = planner.plan_waypoints({{0.00, 0.00}, {0.18, 0.04}, {0.18, 0.16}});
    const auto samples = gantry.follow(traj, 0.002);
    expect(samples.size() > 50, "enough samples");
    const double err = std::hypot(samples.back().ex, samples.back().ey);
    expect(err < 0.008, "final tracking error < 8mm");
  }

  {
    avm::MotionJob job;
    job.waypoints = {{0.0, 0.0}, {0.12, 0.0}, {0.12, 0.10}};
    avm::MotionEngine engine;
    const auto samples = engine.run(job);
    expect(!samples.empty(), "engine samples");
    expect(samples.back().x > 0.10, "engine moved in x");
  }

  if (g_failed == 0) {
    std::cout << "avm_controller_test: all passed\n";
    return 0;
  }
  std::cerr << "avm_controller_test: " << g_failed << " failed\n";
  return 1;
}
