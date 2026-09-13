#include "avm/protocol.hpp"

#include <fstream>
#include <iostream>
#include <string>

int main(int argc, char** argv) {
  if (argc < 2) {
    std::cerr << "usage: avm-motion <job.txt> [output.csv]\n";
    return 2;
  }

  avm::MotionJob job;
  std::string error;
  if (!avm::parse_job_file(argv[1], job, error)) {
    std::cerr << error << '\n';
    return 1;
  }

  avm::MotionEngine engine;
  const auto samples = engine.run(job);

  if (argc >= 3) {
    std::ofstream out(argv[2]);
    if (!out) {
      std::cerr << "cannot write " << argv[2] << '\n';
      return 1;
    }
    avm::write_samples_csv(out, samples);
  } else {
    avm::write_samples_csv(std::cout, samples);
  }

  if (!samples.empty()) {
    const auto& last = samples.back();
    std::cerr << "samples=" << samples.size()
              << " final=(" << last.x << "," << last.y << ")"
              << " err=(" << last.ex << "," << last.ey << ")\n";
  }
  return 0;
}
