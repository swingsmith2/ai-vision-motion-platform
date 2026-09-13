/* Minimal STM32C031 image for Wokwi. Valid vector table + WFI idle.
 * Stops the simulator from loading sketch.ino as a binary (that can blow RAM).
 */
void reset(void);

void *const vectors[] __attribute__((section(".isr_vector"), used)) = {
    (void *)0x20003000u,
    (void *)reset,
};

void reset(void) {
  for (;;) {
    __asm volatile("wfi");
  }
}
