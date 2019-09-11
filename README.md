# Azure Sphere support for PlatformIO

This repository adds support for Azure Sphere boards based on the MT3620 chip, which seems to be the only one available right now. Everything was tested on Avnet Azure Sphere MT3620 Starter Kit. It supports building both high-level and bare-metal (realtime) appliations. A sample of both is included in the "[examples](examples/)" directory (it's the GPIO sample from [azure-sphere-samples](https://github.com/Azure/azure-sphere-samples) repository)

**Note: Not everything in this repository is fully tested yet. Use at your own risk.**

The scripts are based on analyzing the CMake files the official samples use for building and therefore should behave almost identically to building from Visual Studio. You do need to have the official SDK installed since it also uses the same method for finding installed tools and sysroots. This also means no support for building on platforms other than Windows, but it should be possible to port everyting except for the azsphere.exe tool to other platforms easily because the compiler is just gcc (pull requests are welcome!)

## Contributing

If you find any issues, please [report them on GitHub](https://github.com/krzys-h/PlatformIO-platform-azsphere/issues). Any pull requests are welcome too.
