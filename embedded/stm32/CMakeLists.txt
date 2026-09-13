add_library(avm_mcu
  firmware/avm_pid.c
  firmware/avm_app.c
)
target_include_directories(avm_mcu PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/firmware)
target_link_libraries(avm_mcu PUBLIC m)

add_executable(avm-mcu-sim firmware/host_main.c)
target_link_libraries(avm-mcu-sim PRIVATE avm_mcu)

add_executable(avm_mcu_test tests/test_mcu.c)
target_link_libraries(avm_mcu_test PRIVATE avm_mcu)
