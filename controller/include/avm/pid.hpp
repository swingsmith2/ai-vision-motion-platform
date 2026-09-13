#pragma once

#include "avm/types.hpp"

namespace avm {

class PidController {
 public:
  PidController() = default;
  PidController(const PidGains& gains, const PidLimits& limits);

  void set_gains(const PidGains& gains);
  void set_limits(const PidLimits& limits);
  void reset();

  double update(double error, double dt);
  double integral() const { return integral_; }

 private:
  PidGains gains_{};
  PidLimits limits_{};
  double integral_ = 0.0;
  double prev_error_ = 0.0;
  bool has_prev_ = false;
};

}  // namespace avm
