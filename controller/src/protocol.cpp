#include "avm/protocol.hpp"

#include <fstream>
#include <sstream>

namespace avm {

namespace {

bool starts_with(const std::string& s, const std::string& p) {
  return s.rfind(p, 0) == 0;
}

std::vector<std::string> split(const std::string& s, char delim) {
  std::vector<std::string> out;
  std::string cur;
  for (char c : s) {
    if (c == delim) {
      if (!cur.empty()) {
        out.push_back(cur);
        cur.clear();
      }
    } else if (c != ' ' && c != '\t' && c != '\r') {
      cur.push_back(c);
    }
  }
  if (!cur.empty()) {
    out.push_back(cur);
  }
  return out;
}

}  // namespace

std::vector<Sample> MotionEngine::run(const MotionJob& job) {
  TrapezoidalPlanner planner(job.limits);
  GantrySimulator gantry;
  gantry.set_pid(job.gains);
  gantry.set_limits(job.pid_limits);
  gantry.set_plant(job.plant);
  const auto traj = planner.plan_waypoints(job.waypoints);
  return gantry.follow(traj, job.dt);
}

bool parse_job_file(const std::string& path, MotionJob& job, std::string& error) {
  std::ifstream in(path);
  if (!in) {
    error = "cannot open job file: " + path;
    return false;
  }

  std::string line;
  int lineno = 0;
  while (std::getline(in, line)) {
    ++lineno;
    auto hash = line.find('#');
    if (hash != std::string::npos) {
      line = line.substr(0, hash);
    }
    while (!line.empty() && (line.back() == ' ' || line.back() == '\t')) {
      line.pop_back();
    }
    if (line.empty()) {
      continue;
    }

    try {
      if (starts_with(line, "vmax=")) {
        job.limits.vmax = std::stod(line.substr(5));
      } else if (starts_with(line, "amax=")) {
        job.limits.amax = std::stod(line.substr(5));
      } else if (starts_with(line, "dt=")) {
        job.dt = std::stod(line.substr(3));
      } else if (starts_with(line, "pid")) {
        std::istringstream ss(line.substr(3));
        std::string tok;
        while (ss >> tok) {
          if (starts_with(tok, "kp=")) job.gains.kp = std::stod(tok.substr(3));
          if (starts_with(tok, "ki=")) job.gains.ki = std::stod(tok.substr(3));
          if (starts_with(tok, "kd=")) job.gains.kd = std::stod(tok.substr(3));
        }
      } else if (starts_with(line, "waypoint") || starts_with(line, "wp")) {
        const auto pos = line.find(' ');
        if (pos == std::string::npos) {
          error = "bad waypoint at line " + std::to_string(lineno);
          return false;
        }
        const auto parts = split(line.substr(pos + 1), ',');
        if (parts.size() != 2) {
          error = "waypoint must be x,y at line " + std::to_string(lineno);
          return false;
        }
        job.waypoints.emplace_back(std::stod(parts[0]), std::stod(parts[1]));
      } else {
        error = "unknown directive at line " + std::to_string(lineno) + ": " + line;
        return false;
      }
    } catch (const std::exception& ex) {
      error = std::string("parse error at line ") + std::to_string(lineno) + ": " + ex.what();
      return false;
    }
  }

  if (job.waypoints.size() < 2) {
    error = "need at least two waypoints";
    return false;
  }
  return true;
}

void write_samples_csv(std::ostream& out, const std::vector<Sample>& samples) {
  out << "t,x,y,vx,vy,tx,ty,ex,ey\n";
  out.setf(std::ios::fixed);
  out.precision(6);
  for (const auto& s : samples) {
    out << s.t << ',' << s.x << ',' << s.y << ',' << s.vx << ',' << s.vy << ','
        << s.tx << ',' << s.ty << ',' << s.ex << ',' << s.ey << '\n';
  }
}

}  // namespace avm
