#pragma once

#include "avm/gantry.hpp"
#include "avm/trajectory.hpp"
#include "avm/types.hpp"

#include <iosfwd>
#include <string>
#include <vector>

namespace avm {

struct MotionJob {
  MotionLimits limits;
  PidGains gains;
  PidLimits pid_limits;
  PlantParams plant;
  std::vector<Vec2> waypoints;
  double dt = 0.002;
};

class MotionEngine {
 public:
  std::vector<Sample> run(const MotionJob& job);
};

bool parse_job_file(const std::string& path, MotionJob& job, std::string& error);
void write_samples_csv(std::ostream& out, const std::vector<Sample>& samples);

}  // namespace avm
