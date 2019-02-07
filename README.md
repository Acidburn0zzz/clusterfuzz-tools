ClusterFuzz Reproduce Tool
=================================

**This is is not the ClusterFuzz repo. That can be found [here](https://github.com/google/clusterfuzz). This is a tool for reproducing crashes in Chrome that were found by ClusterFuzz.** 

The reproduce tool helps you to reproduce a crash locally that is found by ClusterFuzz infrastructure.

Currently the reproduce tool is supported on:
* Plaforms: **Linux** and **Android** only.
    * For reproducing crashes on **Windows** and **Mac**:
        * For `libFuzzer` and `AFL` testcases, please use the manual instructions [here](https://chromium.googlesource.com/chromium/src/+/master/testing/libfuzzer/reproducing.md).
        * For others, please use the testcase report page to download the testcase first and
then use the command-line and environment options provided in the `crash stacktrace` section
to run the testcase against the target (e.g. chrome, content_shell, d8, etc).

* Sanitizers: **ASan**, **LSan**, **TSan** and **UBSan** only.
    * For reproducing crashes found with **MSan**:
         * Follow the same manual steps cited for **Windows** and **Mac** above.
         * To run the target, please use the manual instructions provided [here](https://www.chromium.org/developers/testing/memorysanitizer#TOC-Running-on-other-distros-using-Docker).


Requirements
---------------

* [gsutil](https://cloud.google.com/storage/docs/gsutil_install)
* `blackbox` and `xdotool`; these can be installed with `apt-get`.


Installation
-----------------

ClusterFuzz tools is a single binary file built with [Pex](https://github.com/pantsbuild/pex).
Therefore, you can simply copy the binary and run it.


For Goobuntu:

1. Run `prodaccess`.
2. Run `/google/data/ro/teams/clusterfuzz-tools/releases/clusterfuzz reproduce -h`.

For others:

1. Download [the latest stable version](https://storage.cloud.google.com/clusterfuzz-tools).
2. Run `clusterfuzz-<version>.pex reproduce -h`.


Usage
------

See `<binary> reproduce --help`. Run it using `<binary> reproduce [testcase-id]`.

Here's the recommended workflow for fixing a bug:

1. Run `<binary> reproduce [testcase-id]`.
2. Make a new branch and make a code change.
3. Run against the code change with `<binary> reproduce [testcase-id] --current`.
4. If the crash doesn’t occur anymore, it means your code change fixes the crash.


Here are some other useful options:

```
  -h, --help            show this help message and exit
  -c, --current         Use the current tree; On the other hand, without
                        --current, the Chrome repository will be switched to
                        the commit specified in the testcase.
  -b {download,chromium,standalone}, --build {download,chromium,standalone}
                        Select which type of build to run the testcase
                        against.
  --disable-goma        Disable GOMA when building binaries locally.
  -j GOMA_THREADS, --goma-threads GOMA_THREADS
                        Manually specify the number of concurrent jobs for a
                        ninja build.
  -l GOMA_LOAD, --goma-load GOMA_LOAD
                        Manually specify maximum load average for a ninja
                        build.
  -i ITERATIONS, --iterations ITERATIONS
                        Specify the number of times to attempt reproduction.
  -dx, --disable-xvfb   Disable running testcases in a virtual frame buffer.
  --target-args TARGET_ARGS
                        Additional arguments for the target (e.g. chrome).
  --edit-mode           Edit args.gn before building and target arguments
                        before running.
  --skip-deps           Skip installing dependencies: gclient sync, gclient
                        runhooks, install-build-deps.sh, and etc.
  --enable-debug        Build Chrome with full debug symbols by injecting
                        `sanitizer_keep_symbols = true` and `is_debug = true`
                        to args.gn. Ready to debug with GDB.
```
