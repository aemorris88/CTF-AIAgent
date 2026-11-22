
from pathlib import Path
import yaml

from harness.sandbox import Sandbox

# Find the attachment downloaded from the CTF website
attachment_dir = Path("browser_artifacts/attachments")
files = list(attachment_dir.glob("*_magicinme"))

if not files:
    raise FileNotFoundError(
        "Could not find the downloaded magicinme attachment."
    )

attachment = files[0]

print("Found attachment:", attachment)
print("File size:", attachment.stat().st_size, "bytes")

# Load the team's existing sandbox configuration
with open("config.yaml", "r", encoding="utf-8") as file:
    config = yaml.safe_load(file)

# Keep the analysis container offline
config["sandbox"]["network_mode"] = "none"

print("\nStarting Docker sandbox...")

with Sandbox(config) as sandbox:
    print("Sandbox started successfully!")

    # Transfer the downloaded file into Docker
    destination = sandbox.put_file(
        local_path=str(attachment),
        rel_name="magicinme"
    )

    print("File transferred to:", destination)

    # Verify the file exists without executing it
    exit_code, output = sandbox.exec(
        "ls -l /work/magicinme"
    )

    print("\nDocker verification:")
    print(output)

    if exit_code == 0:
        print("PASS: Attachment successfully transferred into Docker!")
    else:
        print("FAIL: Could not verify attachment inside Docker.")
