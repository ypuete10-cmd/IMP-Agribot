import os, shutil

SRC = r"C:\Users\yvett\PlantVillage-Dataset\raw\color"
DST = r"C:\Users\yvett\plantvillage_subset\Other"
SKIP = ("Tomato", "Potato", "Pepper")

os.makedirs(DST, exist_ok=True)

for folder in os.listdir(SRC):
    if not folder.startswith(SKIP):
        src = os.path.join(SRC, folder)
        for f in os.listdir(src)[:150]:
            shutil.copy(os.path.join(src, f),
                        os.path.join(DST, f"{folder}_{f}"))
        print(f"Added negatives from {folder}")

print("Done.")