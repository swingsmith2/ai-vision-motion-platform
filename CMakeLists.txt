cmake_minimum_required(VERSION 3.20)
project(avm_platform VERSION 0.1.0 LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE RelWithDebInfo CACHE STRING "Build type" FORCE)
endif()

add_compile_options(-Wall -Wextra -Wpedantic)

add_subdirectory(controller)
add_subdirectory(embedded/stm32)

enable_testing()
add_test(NAME avm_controller_test COMMAND avm_controller_test)
add_test(NAME avm_mcu_test COMMAND avm_mcu_test)
