from os.path import join
from SCons.Script import AlwaysBuild, Builder, Default, DefaultEnvironment
import json
import winreg
import itertools

env = DefaultEnvironment()

# A full list with the available variables
# http://www.scons.org/doc/production/HTML/scons-user.html#app-variables
env.Replace(
    AZSPHERE="azsphere",
    AZSPHERE_SYSROOT=env.BoardConfig().get("build.azsphere_sysroot"),
    PROGSUFFIX=".elf",
)

key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\Microsoft\Azure Sphere", 0, winreg.KEY_READ | winreg.KEY_WOW64_32KEY)
azsphere_install_dir = winreg.QueryValueEx(key, "InstallDir")[0]
subkey_sysroots = winreg.OpenKey(key, "Sysroots", 0, winreg.KEY_READ)
if "AZSPHERE_SYSROOT" not in env or not env["AZSPHERE_SYSROOT"]:
    # if not defined, use the last one available (like the official InitializeCommandPrompt.cmd script)
    try:
        for i in itertools.count():
            name = winreg.EnumKey(subkey_sysroots, i)
            env.Replace(AZSPHERE_SYSROOT=str(name))
    except WindowsError:
        # WindowsError: [Errno 259] No more data is available
        pass
subkey_sysroot = winreg.OpenKey(subkey_sysroots, env["AZSPHERE_SYSROOT"], 0, winreg.KEY_READ)
azsphere_sysroot_install_dir = winreg.QueryValueEx(subkey_sysroot, "InstallDir")[0]
winreg.CloseKey(subkey_sysroot)
winreg.CloseKey(subkey_sysroots)
winreg.CloseKey(key)

env.PrependENVPath('PATH', join(azsphere_install_dir, 'Tools'))
env.PrependENVPath('PATH', join(azsphere_sysroot_install_dir, 'tools', 'gcc'))
env.Append(LIB=[join(azsphere_sysroot_install_dir, 'usr', 'lib')])
env.Append(CPPPATH=[join(azsphere_sysroot_install_dir, 'usr', 'include')])

env.Append(
    CCFLAGS=[
        "-O3",
        "-mcpu=%s" % env.BoardConfig().get("build.cpu"),
        "-mthumb",
    ],
    CXXFLAGS=[
    ],
    LINKFLAGS=[
        "-O3",
        "-mcpu=%s" % env.BoardConfig().get("build.cpu"),
        "-mthumb"
    ],
    CPPDEFINES=[]
)

if env.BoardConfig().get("build.cpu") == "cortex-a7":
    env.Replace(
        AR="arm-poky-linux-musleabi-ar",
        AS="arm-poky-linux-musleabi-as",
        CC="arm-poky-linux-musleabi-gcc",
        CXX="arm-poky-linux-musleabi-g++",
        GDB="arm-poky-linux-musleabi-gdb",
        OBJCOPY="arm-poky-linux-musleabi-objcopy",
        RANLIB="arm-poky-linux-musleabi-gcc-ranlib",
        SIZETOOL="arm-poky-linux-musleabi-size",
    )
    
    env.Append(
        CCFLAGS=[
            "-march=armv7ve",
            "-mfpu=neon",
            "-mfloat-abi=hard",
            "-B", join(azsphere_sysroot_install_dir, 'tools', 'gcc'),
            "--sysroot="+azsphere_sysroot_install_dir,
            "-fPIC",
            "-ffunction-sections",
            "-fdata-sections",
            "-fno-strict-aliasing",
            "-fno-omit-frame-pointer",
            "-fno-exceptions",
            "-fstack-protector-strong",
        ],
        CXXFLAGS=[ #TODO: check
            "-fno-rtti",
            "-fno-exceptions", 
            "-fno-non-call-exceptions",
            "-fno-use-cxa-atexit",
            "-fno-threadsafe-statics",
        ],
        LINKFLAGS=[
            "-march=armv7ve",
            "-mfpu=neon",
            "-mfloat-abi=hard",
            "-B", join(azsphere_sysroot_install_dir, 'tools', 'gcc'),
            "--sysroot="+azsphere_sysroot_install_dir,
            "-nodefaultlibs",
            "-pie",
            "-Wl,--no-undefined",
            "-Wl,--gc-sections"
        ],
        LIBS=["applibs", "pthread", "gcc_s", "c"],
        CPPDEFINES=["_POSIX_C_SOURCE"]
    )
elif env.BoardConfig().get("build.cpu") == "cortex-m4":
    env.Replace(
        AR="arm-none-eabi-ar",
        AS="arm-none-eabi-as",
        CC="arm-none-eabi-gcc",
        CXX="arm-none-eabi-g++",
        GDB="arm-none-eabi-gdb",
        OBJCOPY="arm-none-eabi-objcopy",
        RANLIB="arm-none-eabi-gcc-ranlib",
        SIZETOOL="arm-none-eabi-size",
    )
    
    env.Append(
        CCFLAGS=[ # TODO: what do these do?
            "-MD",
            "-MT",
        ],
        LINKFLAGS=[
            "-nostartfiles",
            "-Wl,--no-undefined",
            "-Wl,-n",
        ],
    )
else:
    raise Exception("Unsupported CPU")

env.Append(
    BUILDERS=dict(
        CreateAppRoot=Builder(
            action=[
                Mkdir("$TARGET"),
                Copy("$TARGET/app_manifest.json", "$PROJECT_DIR/app_manifest.json"),
                Mkdir("$TARGET/bin"),
                Copy("$TARGET/bin/app", "$SOURCE")
            ],
            target_factory=env.fs.Dir
        ),
        CreateImagePackage=Builder(
            action=[
                " ".join([
                    "$AZSPHERE",
                    "image",
                    "package-application",
                    "-v",
                    "--input",
                    "$SOURCE",
                    "--output",
                    "$TARGET",
                    "--sysroot",
                    "$AZSPHERE_SYSROOT"
                ]),
            ],
            suffix=".imagepackage"
        ),
        DeployImagePackage=Builder(
            action=[
                " ".join([
                    "$AZSPHERE",
                    "device",
                    "sideload",
                    "deploy",
                    "-v",
                    "--imagepackage",
                    "$SOURCE"
                ]),
            ]
        )
    )
)

#
# Target: Build executable and linkable firmware
#
target_elf = env.BuildProgram()

#
# Target: Build the .imagepackage file
#
target_approot = env.CreateAppRoot(join("$BUILD_DIR", "approot"), target_elf)
target_imagepackage = env.CreateImagePackage(join("$BUILD_DIR", "firmware"), target_approot)

#
# Target: Upload firmware
#
upload = env.Alias(["upload"], env.DeployImagePackage(target_imagepackage))
AlwaysBuild(upload)

#
# Target: Define targets
#
Default(target_imagepackage)