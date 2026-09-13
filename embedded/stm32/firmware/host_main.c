#include "avm_app.h"

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void write_csv_header(FILE* out) {
  fputs("t,x,y,vx,vy,tx,ty,ex,ey\n", out);
}

static void write_csv_row(FILE* out, AvmState s) {
  fprintf(out, "%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f\n", s.t, s.x, s.y, s.vx, s.vy, s.tx, s.ty, s.ex, s.ey);
}

static float follow_until(float dt, float timeout_s, float err_lim, FILE* csv) {
  float err = 1.0f;
  while (avm_app_state().t < timeout_s) {
    avm_app_step(dt);
    const AvmState s = avm_app_state();
    err = sqrtf(s.ex * s.ex + s.ey * s.ey);
    if (csv) {
      write_csv_row(csv, s);
    }
    if (err < err_lim) {
      break;
    }
  }
  return err;
}

int main(int argc, char** argv) {
  float tx = 0.12f;
  float ty = 0.08f;
  float dt = 0.002f;
  const char* csv_path = NULL;
  int interactive = 0;

  for (int i = 1; i < argc; ++i) {
    if (strcmp(argv[i], "--target") == 0 && i + 1 < argc) {
      sscanf(argv[++i], "%f,%f", &tx, &ty);
    } else if (strcmp(argv[i], "--dt") == 0 && i + 1 < argc) {
      dt = strtof(argv[++i], NULL);
    } else if (strcmp(argv[i], "--csv") == 0 && i + 1 < argc) {
      csv_path = argv[++i];
    } else if (strcmp(argv[i], "--repl") == 0) {
      interactive = 1;
    }
  }

  avm_app_init();
  FILE* csv = NULL;
  if (csv_path) {
    csv = fopen(csv_path, "w");
    if (!csv) {
      fprintf(stderr, "cannot write %s\n", csv_path);
      return 1;
    }
    write_csv_header(csv);
  }

  if (interactive) {
    char line[128];
    char reply[160];
    fputs("avm-mcu-sim repl. 这是本机程序，不会驱动上面的 Wokwi。\n", stderr);
    fputs("一行一条，回车发送：T x y | P kp ki kd | R | S | Q\n", stderr);
    fflush(stderr);
    while (1) {
      fputs("> ", stdout);
      fflush(stdout);
      if (!fgets(line, sizeof(line), stdin)) {
        break;
      }
      line[strcspn(line, "\r\n")] = 0;
      if (line[0] == 0) {
        continue;
      }
      if (line[0] == 'Q' || line[0] == 'q') {
        break;
      }
      if (avm_app_handle_line(line, reply, (int)sizeof(reply))) {
        puts(reply);
        fflush(stdout);
      }
      if ((line[0] == 'T' || line[0] == 't') && strchr(line, ' ')) {
        const float err = follow_until(dt, 2.5f, 0.001f, csv);
        const AvmState s = avm_app_state();
        printf("DONE err=%.5f x=%.4f y=%.4f\n", err, s.x, s.y);
        fflush(stdout);
      }
    }
  } else {
    avm_app_set_target(tx, ty);
    const float err = follow_until(dt, 2.5f, 0.001f, csv);
    const AvmState s = avm_app_state();
    fprintf(stderr, "samples done t=%.3f final=(%.4f,%.4f) err=%.5f\n", s.t, s.x, s.y, err);
    if (err > 0.008f) {
      if (csv) {
        fclose(csv);
      }
      return 1;
    }
  }

  if (csv) {
    fclose(csv);
  }
  return 0;
}
