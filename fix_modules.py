import os

modules_dir = "modules"
files = os.listdir(modules_dir)

for filename in files:
    if filename.endswith(".py"):
        path = os.path.join(modules_dir, filename)
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        module_name = filename[:-3]  # strip .py

        if "def run(" in content:
            if f"{module_name} = run" not in content:
                with open(path, "a", encoding="utf-8") as f:
                    f.write(f"\n\n{module_name} = run\n")
                print(f"✅ Added alias to: {filename}")
            else:
                print(f"✔️ Already has alias: {filename}")
        else:
            print(f"❌ Missing def run(): {filename}")
