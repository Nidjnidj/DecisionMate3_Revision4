import os

modules_dir = "modules"

for filename in os.listdir(modules_dir):
    if filename.endswith(".py") and filename != "__init__.py":
        path = os.path.join(modules_dir, filename)
        module_name = filename[:-3]

        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        content = "".join(lines)

        # Skip files that already have a run() function
        if "def run(" in content:
            if f"{module_name} = run" not in content:
                # Add the alias at the end if missing
                with open(path, "a", encoding="utf-8") as f:
                    f.write(f"\n\n{module_name} = run\n")
                print(f"✅ Alias added to existing run(): {filename}")
            else:
                print(f"✔️ Already OK: {filename}")
            continue

        # Otherwise, wrap the content inside run()
        indent = "    "
        wrapped_lines = [f"def run(T):\n"]
        for line in lines:
            # Skip blank lines at the beginning
            if line.strip() == "" and len(wrapped_lines) == 1:
                continue
            wrapped_lines.append(indent + line)

        wrapped_lines.append(f"\n{module_name} = run\n")

        with open(path, "w", encoding="utf-8") as f:
            f.writelines(wrapped_lines)

        print(f"🔧 Wrapped in run(): {filename}")
