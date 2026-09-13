#include "avm_app.h"
#include "avm_pid.h"

#include <math.h>
#include <stdio.h>

static int failed = 0;

static void expect(int cond, const char* msg) {
  if (!cond) {
    fprintf(stderr, "FAIL: %s\n", msg);
    ++failed;
  }
}

int main(void) {
  {
    AvmPid pid;
    avm_pid_init(&pid, 12.0f, 0.0f, 0.0f);
    const float out = avm_pid_update(&pid, 0.10f, 0.01f);
    expect(fabsf(out - 1.20f) < 1e-5f, "p-only output");
  }

  {
    avm_app_init();
    avm_app_set_target(0.12f, 0.08f);
    for (int i = 0; i < 1200; ++i) {
      avm_app_step(0.002f);
    }
    const AvmState s = avm_app_state();
    const float err = sqrtf(s.ex * s.ex + s.ey * s.ey);
    expect(err < 0.008f, "follow 0.12,0.08 within 8mm");
  }

  {
    char reply[80];
    avm_app_init();
    expect(avm_app_handle_line("T 0.05 0.02", reply, (int)sizeof(reply)), "parse T");
    expect(avm_app_state().tx > 0.04f && avm_app_state().ty > 0.01f, "target stored");
  }

  if (failed == 0) {
    puts("avm_mcu_test: all passed");
    return 0;
  }
  fprintf(stderr, "avm_mcu_test: %d failed\n", failed);
  return 1;
}
