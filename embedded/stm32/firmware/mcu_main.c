#include "avm_app.h"

#include <stdint.h>

#define REG(addr) (*(volatile uint32_t *)(addr))

#define RCC_IOPENR REG(0x40021034u)
#define RCC_APBENR1 REG(0x4002103Cu)
#define GPIOA_MODER REG(0x50000000u)
#define GPIOA_OTYPER REG(0x50000004u)
#define GPIOA_PUPDR REG(0x5000000Cu)
#define GPIOA_BSRR REG(0x50000018u)
#define GPIOA_AFRL REG(0x50000020u)
#define USART2_CR1 REG(0x40004400u)
#define USART2_BRR REG(0x4000440Cu)
#define USART2_ISR REG(0x4000441Cu)
#define USART2_RDR REG(0x40004424u)
#define USART2_TDR REG(0x40004428u)
#define TIM3_CR1 REG(0x40000400u)
#define TIM3_CCMR1 REG(0x40000418u)
#define TIM3_CCER REG(0x40000420u)
#define TIM3_PSC REG(0x40000428u)
#define TIM3_ARR REG(0x4000042Cu)
#define TIM3_CCR1 REG(0x40000434u)
#define TIM3_CCR2 REG(0x40000438u)
#define STK_CTRL REG(0xE000E010u)
#define STK_LOAD REG(0xE000E014u)
#define STK_VAL REG(0xE000E018u)

/* Wokwi Nucleo-C031 按 48 MHz 仿真 */
#define SYSCLK_HZ 48000000u

extern uint32_t _sidata, _sdata, _edata, _sbss, _ebss;
int main(void);
void reset(void);
void hardfault(void);

void *const vectors[] __attribute__((section(".isr_vector"), used)) = {
    (void *)0x20003000u,
    (void *)reset,
    (void *)hardfault,
    (void *)hardfault,
    (void *)hardfault,
    (void *)hardfault,
    (void *)hardfault,
    (void *)hardfault,
    (void *)hardfault,
    (void *)hardfault,
    (void *)hardfault,
    (void *)hardfault,
    (void *)hardfault,
    (void *)hardfault,
    (void *)hardfault,
    (void *)hardfault,
};

void hardfault(void) {
  RCC_IOPENR |= 1u;
  GPIOA_MODER = (GPIOA_MODER & ~(3u << 10)) | (1u << 10);
  for (;;) {
    GPIOA_BSRR = (1u << 5);
    for (volatile int i = 0; i < 80000; ++i) {
    }
    GPIOA_BSRR = (1u << (5 + 16));
    for (volatile int i = 0; i < 80000; ++i) {
    }
  }
}

void reset(void) {
  uint32_t *src = &_sidata;
  uint32_t *dst = &_sdata;
  while (dst < &_edata) {
    *dst++ = *src++;
  }
  dst = &_sbss;
  while (dst < &_ebss) {
    *dst++ = 0;
  }
  main();
  for (;;) {
  }
}

int _close(int fd) {
  (void)fd;
  return -1;
}
int _lseek(int fd, int off, int whence) {
  (void)fd;
  (void)off;
  (void)whence;
  return 0;
}
int _read(int fd, char *buf, int len) {
  (void)fd;
  (void)buf;
  (void)len;
  return 0;
}
int _write(int fd, const char *buf, int len) {
  (void)fd;
  (void)buf;
  return len;
}
int _fstat(int fd, void *st) {
  (void)fd;
  (void)st;
  return 0;
}
int _isatty(int fd) {
  (void)fd;
  return 1;
}

void _exit(int code) {
  (void)code;
  for (;;) {
  }
}

void *_sbrk(int incr) {
  static uint8_t heap[2048];
  static unsigned used = 0;
  if (used + (unsigned)incr > sizeof(heap)) {
    return (void *)-1;
  }
  void *p = heap + used;
  used += (unsigned)incr;
  return p;
}

static void delay_ms(uint32_t ms) {
  STK_CTRL = 0;
  STK_LOAD = (SYSCLK_HZ / 1000u) - 1u;
  STK_VAL = 0;
  STK_CTRL = 5u;
  while (ms--) {
    while ((STK_CTRL & (1u << 16)) == 0) {
    }
  }
  STK_CTRL = 0;
}

static void led(int on) {
  GPIOA_BSRR = on ? (1u << 5) : (1u << (5 + 16));
}

static void uart_putc(char c) {
  while ((USART2_ISR & (1u << 7)) == 0) {
  }
  USART2_TDR = (uint32_t)(uint8_t)c;
}

static void uart_puts(const char *s) {
  while (*s) {
    if (*s == '\n') {
      uart_putc('\r');
    }
    uart_putc(*s++);
  }
}

static int uart_getc_nb(void) {
  if ((USART2_ISR & (1u << 5)) == 0) {
    return -1;
  }
  return (int)(USART2_RDR & 0xFFu);
}

static void hw_init(void) {
  RCC_IOPENR |= 1u;
  RCC_APBENR1 |= (1u << 1) | (1u << 17);

  uint32_t moder = GPIOA_MODER;
  moder &= ~((3u << 4) | (3u << 6) | (3u << 10) | (3u << 12) | (3u << 14));
  moder |= (2u << 4) | (2u << 6) | (1u << 10) | (2u << 12) | (2u << 14);
  GPIOA_MODER = moder;
  GPIOA_OTYPER &= ~((1u << 2) | (1u << 3) | (1u << 5) | (1u << 6) | (1u << 7));
  GPIOA_PUPDR = (GPIOA_PUPDR & ~((3u << 4) | (3u << 6))) | (1u << 6);
  uint32_t afrl = GPIOA_AFRL;
  afrl &= ~((0xFu << 8) | (0xFu << 12) | (0xFu << 24) | (0xFu << 28));
  afrl |= (1u << 8) | (1u << 12) | (1u << 24) | (1u << 28);
  GPIOA_AFRL = afrl;

  USART2_BRR = SYSCLK_HZ / 115200u;
  USART2_CR1 = (1u << 0) | (1u << 2) | (1u << 3);

  /* 48 MHz / 48 = 1 MHz, ARR=20000 → 50 Hz 舵机 PWM */
  TIM3_PSC = 47;
  TIM3_ARR = 19999;
  TIM3_CCMR1 = (6u << 4) | (1u << 3) | (6u << 12) | (1u << 11);
  TIM3_CCER = (1u << 0) | (1u << 4);
  TIM3_CCR1 = 1500;
  TIM3_CCR2 = 1500;
  TIM3_CR1 = (1u << 7) | (1u << 0);
}

static uint32_t pos_to_us(float meters) {
  float n = meters / 0.40f;
  if (n < 0.0f) {
    n = 0.0f;
  }
  if (n > 1.0f) {
    n = 1.0f;
  }
  return 1000u + (uint32_t)(n * 1000.0f);
}

static void apply_outputs(void) {
  const AvmState s = avm_app_state();
  TIM3_CCR1 = pos_to_us(s.x);
  TIM3_CCR2 = pos_to_us(s.y);
  const float err2 = s.ex * s.ex + s.ey * s.ey;
  led(err2 < 0.002f * 0.002f);
}

int main(void) {
  hw_init();
  for (int i = 0; i < 4; ++i) {
    led(1);
    delay_ms(150);
    led(0);
    delay_ms(150);
  }
  avm_app_init();
  avm_app_set_target(0.20f, 0.10f);
  uart_puts("AVM ready. Watch servos + LED.\n");

  char line[96];
  unsigned len = 0;
  char reply[160];
  for (;;) {
    const int ch = uart_getc_nb();
    if (ch >= 0) {
      if (ch == '\n' || ch == '\r') {
        if (len > 0) {
          line[len] = 0;
          if (avm_app_handle_line(line, reply, (int)sizeof(reply))) {
            uart_puts(reply);
            uart_puts("\n");
          }
          len = 0;
        }
      } else if (len + 1 < sizeof(line)) {
        line[len++] = (char)ch;
      }
    }
    avm_app_step(0.002f);
    apply_outputs();
  }
}
