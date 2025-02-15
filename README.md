# Even Realities AGiXT Interface

## Android Dependencies

- Install Termux
- Install dependencies in Termux

```bash
pkg install python git cmake autoconf automake libtool patchelf ninja 
```

## iOS Dependencies

- Install iSH
- Install dependencies in iSH

```bash
apk add python3 git cmake autoconf automake libtool patchelf ninja
```

## Linux Dependencies

- Install dependencies

```bash
sudo apt install python3 git cmake autoconf automake libtool patchelf ninja
```

## Windows Dependencies

- Install Windows Subsystem for Linux (WSL)
- Install Ubuntu 24.04 LTS
- Install dependencies

```bash
sudo apt install python3 git cmake autoconf automake libtool patchelf ninja
```

## Install AGiXT Even Realities package

```bash
pip install agixteven
```

## Usage

Once the depenencies for your operating system are installed, run the AGiXT Even Realities Interface with the following command:

```bash
python -m agixteven --agixt_server "http://localhost:7437" --email "your@email.com" --otp "123456" --agent_name "XT" --wake_word "jarvis"
```
