experiments with python codegen

originally LLVM specific (with llvmlite), but now focusing on C codegen, and hopefully someday OpenCL, Cuda, GLSL, wasm, maybe even javascript.

Main focus is on unrolling and inlining as much code as possible during codegen.
The theory is that this will speed up some computations.
Probably mandelbrot set and other fractals, because those are great.

Uses python 3.7
