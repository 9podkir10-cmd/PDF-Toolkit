cmake_minimum_required(VERSION 3.12)
project(barcodes LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 17)

set(VCPKG_ROOT "C:/vcpkg/installed/x64-windows")

# MuPDF заменю потом
set(MUPDF_INCLUDE_DIR ${VCPKG_ROOT}/include)
set(MUPDF_LIB ${VCPKG_ROOT}/lib/libmupdf.lib)     # libmupdf.lib

# OpenCV
set(OPENCV_INCLUDE_DIR ${VCPKG_ROOT}/include/opencv4)
set(OPENCV_LIBS
    ${VCPKG_ROOT}/lib/opencv_core4.lib
    ${VCPKG_ROOT}/lib/opencv_imgproc4.lib
    ${VCPKG_ROOT}/lib/opencv_imgcodecs4.lib
)

add_executable(barcodes barcodes.cpp)

target_include_directories(barcodes PRIVATE
    ${MUPDF_INCLUDE_DIR}
    ${OPENCV_INCLUDE_DIR}
)

target_link_libraries(barcodes PRIVATE
    ${MUPDF_LIB}
    ${OPENCV_LIBS}
)