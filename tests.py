import os
import sys
import psutil
import time
print(sys.argv[0])
print(['python']+sys.argv)
print(sys.executable)
def restart_script():
    print("Restart")
    path_of_this_script = sys.argv[0]
    python_executable = sys.executable
    os.execl(python_executable,python_executable,*sys.argv)

def main():
    for x in range(1, 10):
        print(x)
        time.sleep(0.5)
        if x == 5:
            restart_script()
if __name__ == "__main__":
    main()