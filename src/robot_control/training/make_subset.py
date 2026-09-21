import os, shutil

SRC = r"C:\Users\yvett\PlantVillage-Dataset\raw\color"
DST = r"C:\Users\yvett\plantvillage_subset"
KEEP = ("Tomato", "Potato", "Pepper")

for folder in os.listdir(SRC):
    if folder.startswith(KEEP):
        shutil.copytree(os.path.join(SRC, folder),
                        os.path.join(DST, folder),
                        dirs_exist_ok=True)
        print(f"Copied {folder}")

print("Done.")