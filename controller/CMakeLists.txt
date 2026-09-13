add_library(avm_controller
  src/pid.cpp
  src/trajectory.cpp
  src/gantry.cpp
  src/protocol.cpp
)
target_include_directories(avm_controller PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_compile_features(avm_controller PUBLIC cxx_std_17)

add_executable(avm-motion src/avm_motion_main.cpp)
target_link_libraries(avm-motion PRIVATE avm_controller)

add_executable(avm_controller_test tests/test_controller.cpp)
target_link_libraries(avm_controller_test PRIVATE avm_controller)
