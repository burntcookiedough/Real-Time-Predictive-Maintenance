import os
import urllib.request

def main():
    hadoop_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "hadoop", "bin"))
    if not os.path.exists(hadoop_dir):
        os.makedirs(hadoop_dir)

    winutils_url = "https://raw.githubusercontent.com/cdarlint/winutils/master/hadoop-3.3.5/bin/winutils.exe"
    hadoop_dll_url = "https://raw.githubusercontent.com/cdarlint/winutils/master/hadoop-3.3.5/bin/hadoop.dll"
    
    print("Downloading winutils.exe...")
    urllib.request.urlretrieve(winutils_url, os.path.join(hadoop_dir, "winutils.exe"))
    print("Downloading hadoop.dll...")
    urllib.request.urlretrieve(hadoop_dll_url, os.path.join(hadoop_dir, "hadoop.dll"))
    print(f"Hadoop binaries installed to {hadoop_dir}")

if __name__ == "__main__":
    main()
